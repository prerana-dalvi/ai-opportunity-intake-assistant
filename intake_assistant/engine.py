"""Assessment engine: intake -> classified, scored, risk-reviewed opportunity brief."""
from __future__ import annotations

from typing import Iterable, List

from . import llm
from .classifier import classify_domain, classify_patterns
from .models import Assessment, UseCaseInput
from .scoring import estimate_savings, priority, responsible_ai_review, score_use_case

PATTERN_CONCEPTS = {
    "Document Intelligence": "extract key fields from incoming documents, validate them against system data, and pre-populate the work item",
    "Knowledge Retrieval (RAG)": "search approved policy manuals and billing rules and return a cited answer in seconds",
    "Workflow Automation": "route, pre-fill and update work items automatically, removing manual re-keying",
    "Decision Support": "score and rank cases so reviewers see the highest-impact items first, with the reasons shown",
    "User Assistance (Copilot/Chat)": "give staff or providers a guided assistant that drafts responses from approved content",
}

PATTERN_METRICS = {
    "Document Intelligence": "Field-extraction accuracy (target >= 95% on validation set)",
    "Knowledge Retrieval (RAG)": "Answer accuracy on golden question set; average handle time",
    "Workflow Automation": "Touchless / straight-through processing rate",
    "Decision Support": "Reviewer agreement rate with AI ranking; time-to-decision",
    "User Assistance (Copilot/Chat)": "First-contact resolution; escalation rate; user satisfaction (CSAT)",
}


def _intake_text(uc: UseCaseInput) -> str:
    return "\n".join([
        f"Title: {uc.title}", f"Business area: {uc.business_area}",
        f"Problem: {uc.problem_statement}", f"Current process: {uc.current_process}",
        f"Desired outcome: {uc.desired_outcome}", f"Data sources: {', '.join(uc.data_sources)}",
    ])


def _template_narrative(uc: UseCaseInput, patterns: List[str], domain: str, hours: float) -> dict:
    lead = patterns[0]
    outcome = (uc.desired_outcome or "Reduce manual effort and improve turnaround").rstrip(".")
    outcome = outcome[:1].lower() + outcome[1:]
    concept = PATTERN_CONCEPTS.get(lead, PATTERN_CONCEPTS["Workflow Automation"])
    summary = (
        f"{uc.business_area} teams face this challenge: {uc.problem_statement.rstrip('.')}. "
        f"This opportunity applies {', '.join(patterns)} within {domain} to "
        f"{outcome}."
    )
    metric = PATTERN_METRICS.get(lead, "Cycle time")
    hypothesis = (
        f"We believe an AI assistant that can {concept} will save about {hours:,.0f} staff hours "
        f"per month for {uc.business_area}, measured by {metric.lower()} and cycle time."
    )
    solution = (
        f"An AI assistant will {concept}. Staff remain in control: the assistant suggests, "
        f"a person confirms. Every suggestion is logged with its source so supervisors can audit it. "
        f"A pilot with one team validates accuracy and adoption before scaling."
    )
    reqs = [
        f"Secure, read-only integration with {', '.join(uc.data_sources[:3]) or 'source systems (TBD)'}",
        "Human review and override for every AI suggestion, with reason codes",
        "Audit log of inputs, outputs, model version and reviewer action",
        "Role-based access aligned to HIPAA minimum-necessary",
        "Baseline metrics captured before pilot (volume, handle time, error rate)",
        "Evaluation dataset and acceptance thresholds agreed with business owner",
    ]
    if uc.involves_phi:
        reqs.append("Deployment only on BAA-covered, approved AI platform")
    questions = [
        "What is the current baseline for volume, handling time and error/rework rate?",
        "Who owns the final decision, and what policy or contract rules govern it?",
        "Which data elements are actually needed (minimum necessary)?",
        "How will success be measured at 30/60/90 days, and who signs off?",
    ]
    if not uc.sponsor:
        questions.insert(0, "Who is the executive sponsor and accountable process owner?")
    return {
        "use_case_summary": summary, "value_hypothesis": hypothesis,
        "solution_concept": solution, "requirements": reqs, "open_questions": questions,
    }


def assess(uc: UseCaseInput, use_llm: bool = True) -> Assessment:
    text = _intake_text(uc)
    patterns = classify_patterns(text)
    domain = classify_domain(text, uc.business_area)
    hours, fte = estimate_savings(uc, patterns)
    scores = score_use_case(uc, patterns, hours)
    pct, quadrant = priority(scores)
    flags = responsible_ai_review(uc, patterns, scores)

    narrative, source = None, "rules"
    if use_llm:
        narrative = llm.draft_narrative(text, patterns, domain)
        source = "llm" if narrative else "rules"
    narrative = narrative or _template_narrative(uc, patterns, domain, hours)

    metrics = [PATTERN_METRICS[p] for p in patterns if p in PATTERN_METRICS]
    metrics.append(f"Staff hours saved per month (target ~{hours:,.0f})")

    return Assessment(
        use_case=uc, ai_patterns=patterns, workflow_domain=domain, scores=scores,
        priority_score=pct, quadrant=quadrant,
        estimated_hours_saved_per_month=hours, estimated_fte_equivalent=fte,
        value_hypothesis=narrative["value_hypothesis"], use_case_summary=narrative["use_case_summary"],
        solution_concept=narrative["solution_concept"], requirements=list(narrative["requirements"]),
        success_metrics=metrics, responsible_ai_flags=flags,
        open_questions=list(narrative["open_questions"]), generated_by=source,
    )


def rank_portfolio(use_cases: Iterable[UseCaseInput], use_llm: bool = False) -> List[Assessment]:
    results = [assess(uc, use_llm=use_llm) for uc in use_cases]
    return sorted(results, key=lambda a: -a.priority_score)
