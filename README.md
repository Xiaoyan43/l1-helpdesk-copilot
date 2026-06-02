# L1 HelpDesk Copilot

> ⚠️ **Personal portfolio / lab only — not a production system.**
> All LLM calls go to the Anthropic API; all Microsoft Graph calls target a **free, isolated
> Microsoft Entra lab tenant**, default `GRAPH_DRY_RUN=true` (simulate, don't modify the tenant).
> Do not point this at any real or production credentials or data.

An IT Support (L1 / Help Desk) portfolio project: take one support ticket →
classify it with Claude → run RAG over a markdown knowledge base to draft a citation-grounded
reply → for account requests, call Microsoft Graph to actually execute the action in a lab
tenant → audit every step.

## What it does
1. **Ingest a ticket** — paste text, or read from a sample CSV.
2. **Classify (Claude)** — category, priority, incident-vs-request, and which KB article is hit.
3. **RAG reply** — retrieve from a markdown KB and draft an L1 reply that cites the relevant articles.
4. **Execute (Microsoft Graph, lab tenant)** — create user / reset password / add to group / assign license.
5. **Audit log** — every classification and action is appended to `audit_log.jsonl`.
6. **Eval** — score the classifier on 50 labeled tickets to get an honest accuracy number.

## Tech stack
Python · FastAPI · Anthropic SDK (Claude) · Microsoft Graph REST (`azure-identity` + `httpx`)
· markdown KB + lightweight retrieval · minimal single-page UI.

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill keys as needed; it also runs with the rule baseline and no keys
uvicorn app.main:app --reload
# UI:   http://127.0.0.1:8000/
# API:  http://127.0.0.1:8000/docs
```
With no keys set, `USE_MOCK_LLM=true` uses a **local rule baseline** for classification — handy for an
offline demo, and the baseline the Claude classifier is measured against. Set `ANTHROPIC_API_KEY`
and `USE_MOCK_LLM=false` to use Claude.

## Eval results
On **50 hand-labeled tickets**, rule baseline (keyword counts) vs. Claude (Haiku 4.5, strict
structured output, `temperature=0` for reproducibility):

| Field | Keyword baseline | Claude | Δ |
|---|---|---|---|
| category | 80% | **92%** | +12 |
| incident vs request | 84% | **98%** | +14 |
| priority | 54% | **74%** | +20 |
| kb_hit | 60% | **72%** | +12 |
| category macro-F1 | 61% | **81%** | +20 |

Reproduce: `python -m eval.run_eval --engine both --show-errors`

**Honest notes / limitations:**
- The test set is only **50 tickets, single-annotator** — for a portfolio demo, not a rigorous benchmark; `temperature=0` makes it reproducible, but on a small set a few points shouldn't be over-read.
- **priority** started at 54% (tied with the baseline). Root cause: the prompt's rubric disagreed with the labels. After tightening the rubric and adding few-shot calibration, it rose to 74%. Priority is inherently subjective.
- **kb_hit** is the noisiest label: ~11/14 "errors" are "I labeled NONE, Claude picked a reasonable KB" — a labeling-convention disagreement, not a model error.
- KB retrieval (BM25) is **independent** of the classifier's kb_hit field — even when the classifier is wrong, retrieval often still cites the right article.

## Microsoft Graph — live-verified
The four account actions ship with `GRAPH_DRY_RUN=true` by default (prints the exact Graph request,
with passwords redacted). Three were **verified live against a real free Entra tenant**:
`create_user → 201` · `reset_password → 204` · `add_to_group → 204`. The app's identity was granted
the **User Administrator** directory role (least privilege); `assign_license` stays dry-run because a
free tenant has no paid SKUs. Setup: [`docs/m365-setup.md`](docs/m365-setup.md).

## Roadmap
- [x] Phase 0 · Scaffold (config / models / runnable FastAPI + rule baseline)
- [x] Phase 1 · Claude structured classification + CSV ingest
- [x] Phase 2 · KB + RAG citation-grounded reply
- [x] Phase 3 · 50-ticket labeled test set + eval script (`python -m eval.run_eval`)
- [x] Phase 4 · Microsoft Graph account actions + audit log (live-verified, see above)
- [x] Phase 5 · Minimal single-page UI (`/`): triage + cited reply + suggested action + audit panel
- [x] Extras · **Confidence-threshold guardrail** (low-confidence triage blocks real actions until human review) + **reply feedback buttons** (resolved / escalate, written to the audit log)

> Interview prep: [`docs/pitch.md`](docs/pitch.md) · demo recording shot list: [`docs/demo-script.md`](docs/demo-script.md)

## Layout
```
app/        FastAPI app (config / models / classifier / kb / responder / graph_actions / audit / main)
kb/         markdown knowledge-base articles
data/       sample tickets CSV (with gold labels)
eval/       eval script (writes eval/last_results.json, gitignored)
docs/       setup guide, interview pitch, demo script
```
