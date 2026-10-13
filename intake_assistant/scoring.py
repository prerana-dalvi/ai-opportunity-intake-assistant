"""Transparent scoring for value, feasibility, data readiness, risk and adoption.

Every score carries a plain-English rationale so senior reviewers and business
leaders can challenge the assumptions instead of trusting a black box.
"""
from __future__ import annotations

from typing import List, Tuple

from .models import DimensionScore, ResponsibleAIFlag, UseCaseInput

WEIGHTS = {
    "Business Value": 0.35,
    "Feasibility": 0.20,
    "Data Readiness": 0.20,
    "Adoption Readiness": 0.15,
    "Risk (inverse)": 0.10,
}

# Conservative share of manual effort an AI assist can realistically remove.
AUTOMATION_RATE = {
    "Workflow Automation": 0.50,
    "Document Intelligence": 0.45,
    "Knowledge Retrieval (RAG)": 0.30,
    "User Assistance (Copilot/Chat)": 0.25,
    "Decision Support": 0.20,   # human still decides; AI speeds review
}

HOURS_PER_FTE_MONTH = 160


def _clamp(x: int) -> int:
    return max(1, min(5, x))


def estimate_savings(uc: UseCaseInput, patterns: List[str]) -> Tuple[float, float]:
    rate = max(AUTOMATION_RATE.get(p, 0.2) for p in patterns)
    if uc.decision_impacts_member_or_provider:
        rate = min(rate, 0.25)  # mandatory human review caps realistic savings
    manual_hours = uc.monthly_volume * uc.minutes_per_item / 60.0
    hours = round(manual_hours * rate, 1)
    return hours, round(hours / HOURS_PER_FTE_MONTH, 2)


def score_use_case(uc: UseCaseInput, patterns: List[str], hours_saved: float) -> List[DimensionScore]:
    scores: List[DimensionScore] = []

    # Business value: driven by recoverable hours, boosted by member/provider experience impact.
    if hours_saved >= 1000:
        v, why = 5, f"~{hours_saved:,.0f} hrs/month recoverable"
    elif hours_saved >= 400:
        v, why = 4, f"~{hours_saved:,.0f} hrs/month recoverable"
    elif hours_saved >= 120:
        v, why = 3, f"~{hours_saved:,.0f} hrs/month recoverable"
    elif hours_saved > 0:
        v, why = 2, f"Only ~{hours_saved:,.0f} hrs/month recoverable"
    else:
        v, why = 2, "Volume/handling time not quantified yet"
    outcome = (uc.desired_outcome + uc.problem_statement).lower()
    if any(k in outcome for k in ("turnaround", "backlog", "abandon", "satisfaction", "timely", "sla")):
        v += 1
        why += "; also improves turnaround/SLA or provider experience"
    scores.append(DimensionScore("Business Value", _clamp(v), why))

    # Feasibility: proven patterns are easier than novel prediction.
    easy = {"Workflow Automation", "Knowledge Retrieval (RAG)", "Document Intelligence"}
    f = 4 if set(patterns) & easy else 3
    why = "Uses mature, well-understood AI patterns" if f == 4 else "Requires model evaluation and tuning"
    if "Decision Support" in patterns and uc.decision_impacts_member_or_provider:
        f -= 1
        why += "; adverse-decision logic needs clinical/policy validation"
    if len(uc.data_sources) > 3:
        f -= 1
        why += f"; integrates {len(uc.data_sources)} data sources"
    scores.append(DimensionScore("Feasibility", _clamp(f), why))

    # Data readiness.
    if not uc.data_sources:
        d, why = 1, "No data sources identified yet"
    elif uc.data_is_structured is True:
        d, why = 4, "Structured data available in source systems"
    elif uc.data_is_structured is False:
        d, why = 3, "Unstructured content (documents/notes) needs extraction and labeling"
    else:
        d, why = 2, "Data structure/quality not yet confirmed"
    scores.append(DimensionScore("Data Readiness", _clamp(d), why))

    # Risk (higher = riskier).
    r, reasons = 1, []
    if uc.involves_phi:
        r += 1; reasons.append("handles PHI")
    if uc.decision_impacts_member_or_provider:
        r += 2; reasons.append("can affect member/provider outcomes")
    if "User Assistance (Copilot/Chat)" in patterns:
        r += 1; reasons.append("generative answers can hallucinate")
    scores.append(DimensionScore("Risk", _clamp(r), ", ".join(reasons) or "Internal, low-impact workflow"))

    # Adoption readiness.
    a, why = 2, "Needs an executive sponsor and named process owners"
    if uc.sponsor:
        a += 1; why = f"Sponsor identified ({uc.sponsor})"
    if len(uc.stakeholders) >= 2:
        a += 1; why += f"; {len(uc.stakeholders)} stakeholder groups engaged"
    if "assist" in uc.desired_outcome.lower() or "Knowledge Retrieval (RAG)" in patterns:
        a += 1; why += "; assistive design keeps staff in control (lower change resistance)"
    scores.append(DimensionScore("Adoption Readiness", _clamp(a), why))
    return scores


def priority(scores: List[DimensionScore]) -> Tuple[float, str]:
    s = {d.name: d.score for d in scores}
    weighted = (
        s["Business Value"] * WEIGHTS["Business Value"]
        + s["Feasibility"] * WEIGHTS["Feasibility"]
        + s["Data Readiness"] * WEIGHTS["Data Readiness"]
        + s["Adoption Readiness"] * WEIGHTS["Adoption Readiness"]
        + (6 - s["Risk"]) * WEIGHTS["Risk (inverse)"]
    )
    pct = round(weighted / 5 * 100, 1)
    value = s["Business Value"]
    ease = (s["Feasibility"] + s["Data Readiness"]) / 2
    if value >= 4 and ease >= 3.5:
        quadrant = "Quick Win"
    elif value >= 4:
        quadrant = "Strategic Bet"
    elif ease >= 3.5:
        quadrant = "Incremental Improvement"
    else:
        quadrant = "Revisit Later"
    return pct, quadrant


def responsible_ai_review(uc: UseCaseInput, patterns: List[str], data_scores: List[DimensionScore]) -> List[ResponsibleAIFlag]:
    flags: List[ResponsibleAIFlag] = []
    if uc.involves_phi:
        flags.append(ResponsibleAIFlag(
            "Privacy / PHI", "High",
            "Workflow processes Protected Health Information.",
            "Use only BAA-covered, approved AI services; apply minimum-necessary access; "
            "redact identifiers before prompts; log access for HIPAA audit.",
            escalate=False,
        ))
    if uc.decision_impacts_member_or_provider:
        flags.append(ResponsibleAIFlag(
            "Human Oversight", "High",
            "Output could influence a denial, payment, or enrollment decision.",
            "AI recommends only; a qualified human makes and documents the final decision. "
            "Confirm alignment with state Medicaid contract and CMS requirements.",
            escalate=True,
        ))
    if "Decision Support" in patterns:
        flags.append(ResponsibleAIFlag(
            "Bias / Fairness", "Medium",
            "Prioritization or risk models may treat provider types or regions unevenly.",
            "Test outcomes across provider type, region and language; monitor drift quarterly.",
        ))
    if "User Assistance (Copilot/Chat)" in patterns or "Knowledge Retrieval (RAG)" in patterns:
        flags.append(ResponsibleAIFlag(
            "Accuracy / Hallucination", "Medium",
            "Generated answers may be wrong or out of date.",
            "Ground answers in approved sources with citations; show 'I don't know' when "
            "confidence is low; run a golden-question evaluation set before release.",
        ))
    if any(d.name == "Data Readiness" and d.score <= 2 for d in data_scores):
        flags.append(ResponsibleAIFlag(
            "Operational Risk", "Medium",
            "Data readiness is unconfirmed.",
            "Run a data profiling sprint with the data team before committing to a build.",
        ))
    return flags
