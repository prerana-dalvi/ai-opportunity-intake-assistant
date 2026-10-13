"""Optional generative-AI layer (Anthropic Claude API).

The project runs fully offline with deterministic templates. If the
`anthropic` package is installed and ANTHROPIC_API_KEY is set, the LLM
drafts richer narrative text. Scores and risk flags are NEVER delegated to
the LLM, so results stay explainable and reproducible.

Guardrails applied here:
  * All input is PHI-redacted before it leaves the machine.
  * The model must return strict JSON; malformed output falls back to templates.
  * Q&A answers must cite retrieved sources or say they don't know.
"""
from __future__ import annotations

import json
import os
from typing import List, Optional

from .phi_guard import redact
from .retrieval import Hit

DEFAULT_MODEL = os.getenv("AI_INTAKE_MODEL", "claude-sonnet-5-5")

SYSTEM_PROMPT = """You are an AI Business Partner in a healthcare technology Center of Excellence
supporting Medicaid provider and claims platforms. Translate business pain points into
clear, practical AI use cases for non-technical leaders. Be concrete and conservative:
never promise accuracy you cannot verify, always keep a human accountable for decisions
that affect members or providers, and respect HIPAA minimum-necessary principles."""


def llm_available() -> bool:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _client():
    import anthropic
    return anthropic.Anthropic()


def _call(prompt: str, max_tokens: int = 1200) -> str:
    resp = _client().messages.create(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def draft_narrative(intake_text: str, patterns: List[str], domain: str) -> Optional[dict]:
    """Return {use_case_summary, value_hypothesis, solution_concept, requirements[], open_questions[]} or None."""
    if not llm_available():
        return None
    safe = redact(intake_text).text
    prompt = f"""Intake notes (identifiers redacted):
<intake>
{safe}
</intake>
Workflow domain: {domain}
Candidate AI patterns: {", ".join(patterns)}

Return ONLY a JSON object with keys:
"use_case_summary" (2-3 sentences), "value_hypothesis" (one 'We believe... will... measured by...' sentence),
"solution_concept" (3-4 sentences, human-in-the-loop), "requirements" (5-7 short strings),
"open_questions" (3-5 short strings for the next discovery session)."""
    try:
        raw = _call(prompt)
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end + 1])
        required = {"use_case_summary", "value_hypothesis", "solution_concept", "requirements", "open_questions"}
        return data if required.issubset(data) else None
    except Exception:
        return None  # graceful degradation to templates


def grounded_answer(question: str, hits: List[Hit]) -> str:
    """Answer only from retrieved passages, with [n] citations."""
    if not hits:
        return "I couldn't find this in the approved knowledge base. Please route to a subject-matter expert."
    if not llm_available():
        top = hits[0].chunk
        return f"{top.text.strip()}\n\n[1] {top.source} > {top.heading}"
    context = "\n\n".join(f"[{i}] ({h.chunk.source} > {h.chunk.heading})\n{h.chunk.text}" for i, h in enumerate(hits, 1))
    prompt = f"""Answer the question using ONLY the numbered sources. Cite like [1].
If the sources don't contain the answer, say so plainly.
<sources>
{context}
</sources>
Question: {redact(question).text}"""
    try:
        return _call(prompt, max_tokens=600)
    except Exception:
        top = hits[0].chunk
        return f"{top.text.strip()}\n\n[1] {top.source} > {top.heading}"
