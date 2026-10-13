import json
from pathlib import Path

import pytest

from intake_assistant import UseCaseInput, assess, rank_portfolio
from intake_assistant.classifier import classify_domain, classify_patterns
from intake_assistant.phi_guard import redact
from intake_assistant.report import intake_brief, portfolio_table
from intake_assistant.retrieval import BM25Index, load_chunks

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = [UseCaseInput(**d) for d in json.loads((ROOT / "data/sample_use_cases.json").read_text())]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


# ---------- PHI guardrail ----------
@pytest.mark.parametrize("text,label", [
    ("SSN 123-45-6789", "SSN"),
    ("call 512-555-0100", "PHONE"),
    ("DOB 04/12/1980", "DATE"),
    ("NPI 1234567893", "NPI"),
    ("Medicaid ID: GA12345678", "MEMBER_ID"),
    ("email jane.doe@example.com", "EMAIL"),
    ("Claim ID: 2026-0001234", "CLAIM_ID"),
])
def test_redacts_identifiers(text, label):
    res = redact(text)
    assert f"[REDACTED-{label}]" in res.text
    assert res.counts[label] == 1


def test_redact_leaves_clean_text_untouched():
    clean = "Pended claims age past SLA because examiners self-assign."
    assert redact(clean).text == clean
    assert not redact(clean).found_any


# ---------- classification ----------
def test_classifies_document_intelligence():
    assert "Document Intelligence" in classify_patterns("re-key data from uploaded PDF license forms")


def test_classifies_claims_domain():
    assert classify_domain("pended claims with denial edits") == "Claims Processing"


def test_unknown_text_has_safe_defaults():
    assert classify_patterns("zzz") == ["Workflow Automation"]
    assert classify_domain("zzz") == "General Operations"


# ---------- scoring & responsible AI ----------
def test_adverse_decision_requires_escalation():
    pa = assess(SAMPLES[3], use_llm=False)
    oversight = [f for f in pa.responsible_ai_flags if f.category == "Human Oversight"]
    assert oversight and oversight[0].escalate


def test_phi_flag_raised_only_when_phi_present():
    call_center = assess(SAMPLES[0], use_llm=False)
    claims = assess(SAMPLES[2], use_llm=False)
    assert not any(f.category == "Privacy / PHI" for f in call_center.responsible_ai_flags)
    assert any(f.category == "Privacy / PHI" for f in claims.responsible_ai_flags)


def test_scores_within_bounds_and_deterministic():
    a1, a2 = assess(SAMPLES[1], use_llm=False), assess(SAMPLES[1], use_llm=False)
    assert all(1 <= s.score <= 5 for s in a1.scores)
    assert a1.priority_score == a2.priority_score
    assert 0 < a1.priority_score <= 100


def test_human_review_caps_savings():
    uc = UseCaseInput(**{**SAMPLES[2].to_dict(), "decision_impacts_member_or_provider": True})
    capped = assess(uc, use_llm=False).estimated_hours_saved_per_month
    uncapped = assess(SAMPLES[2], use_llm=False).estimated_hours_saved_per_month
    assert capped < uncapped


def test_portfolio_ranked_descending_and_low_value_last():
    ranked = rank_portfolio(SAMPLES)
    scores = [a.priority_score for a in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[-1].use_case.title == "Weekly Status Report Drafting"


def test_reports_render_without_phi():
    uc = UseCaseInput(**{**SAMPLES[2].to_dict(), "problem_statement": "Member ID: GA99887766 claim stuck in pend queue"})
    brief = intake_brief(assess(uc, use_llm=False))
    assert "GA99887766" not in brief and "[REDACTED-MEMBER_ID]" in brief
    assert "Responsible AI review" in brief
    assert "Rank" in portfolio_table(rank_portfolio(SAMPLES))


# ---------- retrieval ----------
def test_retrieval_finds_relevant_policy():
    idx = BM25Index(load_chunks(ROOT / "data/knowledge_base"))
    hits = idx.search("does a claim denial need human review")
    assert hits and hits[0].chunk.heading == "Human oversight"


def test_retrieval_returns_nothing_for_off_topic():
    idx = BM25Index(load_chunks(ROOT / "data/knowledge_base"))
    assert idx.search("recipe for banana bread") == []
