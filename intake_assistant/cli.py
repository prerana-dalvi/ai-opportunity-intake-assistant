"""Command-line interface.

Examples:
  python -m intake_assistant portfolio data/sample_use_cases.json --out reports/
  python -m intake_assistant assess data/sample_use_cases.json --index 0
  python -m intake_assistant ask "Does every AI suggestion need human review?"
  python -m intake_assistant redact "Member ID: ABC123456 called from 512-555-0100"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import assess, rank_portfolio
from .llm import grounded_answer, llm_available
from .models import UseCaseInput
from .phi_guard import redact
from .report import intake_brief, portfolio_table
from .retrieval import BM25Index, load_chunks

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "data" / "knowledge_base"


def load_use_cases(path: str):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [UseCaseInput(**item) for item in raw]


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:60]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="intake_assistant", description="AI Opportunity Intake Assistant")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("assess", help="Assess one use case and print an intake brief")
    a.add_argument("file"); a.add_argument("--index", type=int, default=0)
    a.add_argument("--no-llm", action="store_true")

    pf = sub.add_parser("portfolio", help="Rank all use cases and write briefs")
    pf.add_argument("file"); pf.add_argument("--out", default="reports")
    pf.add_argument("--no-llm", action="store_true")

    q = sub.add_parser("ask", help="Ask the responsible-AI / claims knowledge base")
    q.add_argument("question")

    r = sub.add_parser("redact", help="Redact PHI/PII from text")
    r.add_argument("text")

    args = p.parse_args(argv)

    if args.cmd == "assess":
        uc = load_use_cases(args.file)[args.index]
        print(intake_brief(assess(uc, use_llm=not args.no_llm)))
    elif args.cmd == "portfolio":
        results = rank_portfolio(load_use_cases(args.file), use_llm=not args.no_llm)
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        (out / "portfolio.md").write_text(portfolio_table(results), encoding="utf-8")
        for res in results:
            (out / f"{_slug(res.use_case.title)}.md").write_text(intake_brief(res), encoding="utf-8")
        print(portfolio_table(results))
        print(f"Wrote {len(results) + 1} files to {out}/ (LLM narrative: {'on' if llm_available() and not args.no_llm else 'off'})")
    elif args.cmd == "ask":
        hits = BM25Index(load_chunks(KB_DIR)).search(args.question)
        print(grounded_answer(args.question, hits))
    elif args.cmd == "redact":
        res = redact(args.text)
        print(res.text); print(f"Redactions: {res.counts or 'none'}")
    return 0
