"""Retrieval evaluation against a golden question set.

Measures Hit@1, Hit@3 and correct abstention (no answer for out-of-scope
questions). Exits non-zero if quality drops below thresholds so CI catches
regressions — the same release-gate idea used in software QA, applied to AI.

    python evals/run_retrieval_eval.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intake_assistant.retrieval import BM25Index, load_chunks  # noqa: E402

THRESHOLDS = {"hit@1": 0.80, "hit@3": 0.90, "abstention": 1.0}


def main() -> int:
    idx = BM25Index(load_chunks(ROOT / "data" / "knowledge_base"))
    golden = json.loads((ROOT / "evals" / "golden_questions.json").read_text())
    in_scope = [g for g in golden if g["expected_heading"]]
    out_scope = [g for g in golden if not g["expected_heading"]]

    h1 = h3 = abstain = 0
    print(f"{'RESULT':7} {'QUESTION':62} TOP HIT")
    for g in golden:
        hits = idx.search(g["question"], k=3)
        heads = [h.chunk.heading for h in hits]
        if g["expected_heading"]:
            ok1 = bool(heads) and heads[0] == g["expected_heading"]
            ok3 = g["expected_heading"] in heads
            h1 += ok1; h3 += ok3
            status = "PASS" if ok1 else ("TOP3" if ok3 else "FAIL")
        else:
            ok = not hits
            abstain += ok
            status = "PASS" if ok else "FAIL"
        print(f"{status:7} {g['question'][:62]:62} {heads[0] if heads else '(abstained)'}")

    metrics = {
        "hit@1": h1 / len(in_scope),
        "hit@3": h3 / len(in_scope),
        "abstention": abstain / len(out_scope) if out_scope else 1.0,
    }
    print("\nMetric       Score   Threshold")
    failed = False
    for k, v in metrics.items():
        ok = v >= THRESHOLDS[k]
        failed |= not ok
        print(f"{k:12} {v:6.0%}   {THRESHOLDS[k]:.0%}  {'✓' if ok else '✗'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
