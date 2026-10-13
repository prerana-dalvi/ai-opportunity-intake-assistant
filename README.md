# 🩺 AI Opportunity Intake Assistant

**Turn healthcare provider and claims pain points into scored, responsible AI use cases — in minutes, not weeks.**

[![CI](https://github.com/<your-username>/ai-opportunity-intake-assistant/actions/workflows/ci.yml/badge.svg)](../../actions)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

An AI Center of Excellence receives a steady stream of "can AI help with this?" requests from claims, provider enrollment, utilization management and contact-center teams. This tool supports the **AI Business Partner** workflow end to end:

```
Discovery notes ──► Classify ──► Score ──► Responsible AI review ──► Intake brief ──► Ranked portfolio
                   (AI pattern   (value,     (PHI, human oversight,    (summary, value    (value vs. ease,
                    + domain)    feasibility, bias, hallucination,      hypothesis, reqs,  capacity freed)
                                 data, risk,  escalation)               metrics, open Qs)
                                 adoption)
```

> All data in this repository is synthetic. The playbook and glossary are illustrative samples written for this project, not any organization's actual policy.

---

## Why I built this

After 15+ years in quality engineering on Medicaid MMIS, provider management and medical bill processing programs, I wanted a hands-on project that applies AI where I know the work best: **provider and claims operations**. The design choices reflect what I've seen matter in public-sector healthcare IT — explainable decisions, HIPAA-aware data handling, human accountability, and test evidence before anything ships.

## What it demonstrates

| Skill area | Where to look |
|---|---|
| Translating business needs into AI use cases, value hypotheses and requirements | `intake_assistant/engine.py`, `sample_output/*.md` |
| Assessing feasibility, value, risk, data readiness and adoption | `intake_assistant/scoring.py` — every score has a written rationale |
| Prioritization and business-case inputs | Portfolio ranking + value/ease quadrant + hours/FTE estimate |
| Responsible AI: human oversight, PHI, compliance, escalation | `responsible_ai_review()` + `intake_assistant/phi_guard.py` |
| Generative AI with guardrails | `intake_assistant/llm.py` — Claude API, PHI redaction before prompts, strict JSON, graceful fallback |
| Knowledge retrieval (RAG) with citations and abstention | `intake_assistant/retrieval.py` (BM25) + grounded answering |
| AI quality evaluation as a release gate | `evals/run_retrieval_eval.py` — Hit@1, Hit@3, abstention thresholds in CI |
| Reusable tools and templates for the intake process | CLI, Streamlit UI, markdown brief template |

## Design principles

1. **Scores are rules, narratives can be AI.** Prioritization must be explainable and reproducible, so scoring is deterministic. The LLM only drafts prose.
2. **The AI recommends; a person decides.** Any use case that could affect a member or provider is flagged for human oversight and governance escalation, and its savings estimate is capped to reflect review time.
3. **Minimum necessary.** Identifiers (SSN, member ID, NPI, MRN, claim ID, DOB, phone, email) are redacted before text reaches a model or a report.
4. **Say "I don't know."** Retrieval abstains on out-of-scope questions instead of guessing; the eval set tests that explicitly.
5. **Works offline.** No API key required; add one to unlock Claude-drafted narratives.

## Quick start

```bash
git clone https://github.com/<your-username>/ai-opportunity-intake-assistant.git
cd ai-opportunity-intake-assistant
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Rank the sample portfolio and write one intake brief per opportunity
python -m intake_assistant portfolio data/sample_use_cases.json --out reports --no-llm

# Ask the responsible-AI playbook / claims glossary (cited answer)
python -m intake_assistant ask "Can AI deny a prior authorization on its own?"

# Redact identifiers
python -m intake_assistant redact "Medicaid ID: GA12345678 called from 512-555-0100"

# Web UI
streamlit run app.py

# Tests + AI quality gate
pytest -q
python evals/run_retrieval_eval.py
```

Optional: copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY`, and drop `--no-llm` to have Claude draft the use-case summary, value hypothesis, solution concept, requirements and discovery questions.

## Sample output

```
| Rank | Opportunity                               | Domain                             | Priority | Quadrant                | Hrs/mo | Escalate |
|------|-------------------------------------------|------------------------------------|----------|-------------------------|--------|----------|
| 1    | Pended Claims Triage and Routing          | Claims Processing                  | 90.0     | Quick Win               | 1,000  |          |
| 2    | Provider Call Center Policy Assistant     | Provider Services / Contact Center | 86.0     | Quick Win               | 900    |          |
| 3    | Provider Enrollment Document Intelligence | Provider Enrollment & Data         | 84.0     | Quick Win               | 412    | ⚠️       |
| 4    | Prior Authorization Clinical Summary      | Prior Authorization / UM           | 78.0     | Strategic Bet           | 625    | ⚠️       |
| 5    | Weekly Status Report Drafting             | General Operations                 | 65.0     | Incremental Improvement | 30     |          |
```

See [`sample_output/`](sample_output/) for full intake briefs, e.g. [Prior Authorization Clinical Summary](sample_output/prior-authorization-clinical-summary.md).

Retrieval evaluation (golden set of 14 questions, including one deliberately out-of-scope):

```
Metric       Score   Threshold
hit@1          92%   80%  ✓
hit@3         100%   90%  ✓
abstention    100%  100%  ✓
```

The one Hit@1 miss ("Can the AI automatically deny a claim…") ranks the *Pended claim* glossary entry above *Human oversight* because of keyword overlap — a known limit of lexical search and the next improvement on the roadmap.

## How scoring works

| Dimension | Weight | Driven by |
|---|---|---|
| Business Value | 35% | Recoverable hours (volume × handle time × realistic automation rate), SLA/experience impact |
| Feasibility | 20% | Maturity of the AI pattern, adverse-decision complexity, number of integrations |
| Data Readiness | 20% | Sources identified, structured vs. unstructured |
| Adoption Readiness | 15% | Sponsor, stakeholder coverage, assistive vs. autonomous design |
| Risk (inverse) | 10% | PHI, member/provider impact, generative output |

Quadrants: **Quick Win** (high value, easy), **Strategic Bet** (high value, harder), **Incremental Improvement**, **Revisit Later**. Weights live in one dictionary so a CoE can tune them.

## Project structure

```
intake_assistant/
  models.py       # UseCaseInput, Assessment, scores, risk flags
  classifier.py   # AI pattern + workflow domain classification
  scoring.py      # value / feasibility / data / risk / adoption + responsible AI review
  phi_guard.py    # identifier redaction
  retrieval.py    # BM25 retrieval over the knowledge base
  llm.py          # optional Claude layer with guardrails
  engine.py       # assess() and rank_portfolio()
  report.py       # markdown intake brief + portfolio table
  cli.py          # assess | portfolio | ask | redact
app.py            # Streamlit UI
data/             # synthetic use cases + sample knowledge base
evals/            # golden questions + retrieval quality gate
tests/            # unit tests (pytest)
```

## Roadmap

- Hybrid retrieval (BM25 + embeddings) to fix the lexical miss above
- Stakeholder feedback capture and adoption tracking after go-live
- Export intake brief to a slide-ready one-pager
- LLM-as-judge evaluation for generated narratives, with human spot-check sampling

## Author

**Prerana Dalvi** — Quality engineering leader in Medicaid / federal healthcare IT, upskilling in applied AI, RAG and AI quality evaluation.
[LinkedIn](https://www.linkedin.com/in/prerana-dalvi)

MIT licensed.
