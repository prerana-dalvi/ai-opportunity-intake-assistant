"""PHI / PII guardrail.

Redacts common identifiers *before* any text is sent to an external LLM or
written to a report. This is a demonstration control, not a certified HIPAA
de-identification method (see 45 CFR 164.514 Safe Harbor / Expert Determination).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Order matters: more specific patterns first.
_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("PHONE", re.compile(r"\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("DATE", re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b")),
    ("NPI", re.compile(r"\bNPI[:#\s]*\d{10}\b", re.IGNORECASE)),
    ("MEMBER_ID", re.compile(r"\b(?:member|medicaid|subscriber|patient)\s*(?:id|#|no\.?)[:#\s]*[A-Z0-9]{6,15}\b", re.IGNORECASE)),
    ("MRN", re.compile(r"\bMRN[:#\s]*[A-Z0-9]{5,12}\b", re.IGNORECASE)),
    ("CLAIM_ID", re.compile(r"\bclaim\s*(?:id|#|no\.?)[:#\s]*[A-Z0-9-]{6,20}\b", re.IGNORECASE)),
]


@dataclass
class RedactionResult:
    text: str
    counts: Dict[str, int]

    @property
    def found_any(self) -> bool:
        return any(self.counts.values())


def redact(text: str) -> RedactionResult:
    """Replace identifiers with typed placeholders like [REDACTED-SSN]."""
    counts: Dict[str, int] = {}
    out = text or ""
    for label, pattern in _PATTERNS:
        out, n = pattern.subn(f"[REDACTED-{label}]", out)
        if n:
            counts[label] = counts.get(label, 0) + n
    return RedactionResult(text=out, counts=counts)
