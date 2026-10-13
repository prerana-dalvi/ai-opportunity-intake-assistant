"""Map a business problem to AI solution patterns and a healthcare workflow domain.

Deterministic keyword matching keeps results explainable and testable; the
optional LLM layer (llm.py) can refine the narrative but never the scores.
"""
from __future__ import annotations

import re
from typing import Dict, List

AI_PATTERNS: Dict[str, List[str]] = {
    "Document Intelligence": [
        "fax", "pdf", "scan", "attachment", "medical record", "form", "document",
        "ocr", "extract", "w-9", "license", "clinical notes", "paper",
    ],
    "Knowledge Retrieval (RAG)": [
        "policy", "manual", "look up", "lookup", "search", "find the answer",
        "guideline", "knowledge", "reference", "billing rules", "fee schedule", "faq",
    ],
    "Workflow Automation": [
        "manual", "re-key", "rekey", "copy", "data entry", "route", "queue",
        "repetitive", "spreadsheet", "status update", "handoff", "backlog", "pend",
    ],
    "Decision Support": [
        "review", "determine", "triage", "prioritize", "denial", "medical necessity",
        "risk", "predict", "fraud", "anomaly", "flag", "edit", "adjudicat",
    ],
    "User Assistance (Copilot/Chat)": [
        "call center", "caller", "phone", "portal", "chat", "provider questions",
        "help desk", "agent", "inquiry", "inquiries", "self-service", "email",
    ],
}

WORKFLOW_DOMAINS: Dict[str, List[str]] = {
    "Claims Processing": ["claim", "adjudicat", "denial", "remittance", "835", "837", "edit", "pend"],
    "Provider Enrollment & Data": ["provider enrollment", "credential", "npi", "revalidat", "provider data", "enrollment"],
    "Prior Authorization / UM": ["prior auth", "authorization", "utilization", "medical necessity", "pa request"],
    "Provider Services / Contact Center": ["call center", "provider services", "inquiry", "inquiries", "help desk", "portal"],
    "Care Management": ["care management", "care plan", "case manager", "outreach"],
    "Program Integrity": ["fraud", "waste", "abuse", "audit", "overpayment"],
}


def _hits(text: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if re.search(re.escape(kw), text))


def classify_patterns(text: str, max_patterns: int = 3) -> List[str]:
    t = text.lower()
    scored = [(name, _hits(t, kws)) for name, kws in AI_PATTERNS.items()]
    scored = [s for s in scored if s[1] > 0]
    scored.sort(key=lambda s: (-s[1], s[0]))
    return [name for name, _ in scored[:max_patterns]] or ["Workflow Automation"]


def classify_domain(text: str, business_area: str = "") -> str:
    """Pick the workflow domain; the stakeholder's own business area counts double."""
    t, area = text.lower(), business_area.lower()
    scored = [(name, _hits(t, kws) + 2 * _hits(area, kws)) for name, kws in WORKFLOW_DOMAINS.items()]
    scored.sort(key=lambda s: (-s[1], s[0]))
    return scored[0][0] if scored[0][1] > 0 else "General Operations"
