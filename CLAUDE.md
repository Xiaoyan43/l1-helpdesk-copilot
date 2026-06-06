# CLAUDE.md — L1 Help Desk Copilot (project memory / handoff)

> Read this first in any new session. It carries the project state so you don't need prior chat history.
> Pair it with [`ROADMAP.md`](ROADMAP.md) for what to build next.

## What this is
An IT Support (L1 / Help Desk) **portfolio / lab** project (not production). It's a real
**Service Desk ticket workspace**: a persistent SQLite ticket queue with an ITSM lifecycle
(New → In Progress → Waiting User → Escalated → Resolved), fields (category / priority /
**impact** / **urgency** / SLA risk / requester / channel), Incident vs Service Request,
**escalation reason + L2 team**, **resolution codes**, and a per-ticket **timeline** — with
**Claude as the L1 copilot** on top. Per-ticket pipeline: **classify** with Claude (category /
priority / impact / urgency / incident-vs-request / KB hit) → **RAG** over a markdown KB → cited L1
reply → for account requests, **Microsoft Graph** actions on a free lab Entra tenant (default
dry-run), recorded on the timeline. Plus a confidence guardrail, human-in-the-loop feedback, and a
60-ticket eval harness.

- **Repo:** https://github.com/Xiaoyan43/l1-helpdesk-copilot (public)
- **Live demo:** https://l1-helpdesk-copilot.onrender.com (public, **mock mode**)
- **Status:** Phases 0–6 done + extras. Live-deployed. See ROADMAP.md for next work.

## Run / test / deploy
```bash
# setup
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env            # optional; runs fine with no keys (mock + dry-run)

# run (UI at http://127.0.0.1:8000/, API docs at /docs)
uvicorn app.main:app --reload

# eval (baseline vs Claude on the 60-ticket labelled set)
python -m eval.run_eval --engine both --show-errors

# optional: upgrade retrieval to semantic embeddings (heavy, pulls torch)
pip install -r requirements-rag.txt
```
Deploy: `render.yaml` blueprint runs the public **mock** demo (free tier). No tests/CI yet (see ROADMAP).

## Architecture (file map)
```
app/
  main.py          FastAPI routes: UI "/", /tickets (+ /{id}, /triage, /respond, /respond/stream, /status, /escalate,
                   /resolve, /comment), /classify, /respond, /actions/*, /graph/*, /audit, /feedback, /healthz
  config.py        pydantic-settings; .env-first source order; defaults = mock + dry-run; tickets_db_path
  models.py        pydantic schemas (Ticket, Classification[+impact/urgency], StoredTicket, TimelineEvent,
                   TicketStatus/Impact/Urgency/Channel/EscalationTeam/ResolutionCode enums, ActionResult, ...)
  classifier.py    rule_based_classify (baseline) + llm_classify (Claude, strict tool-use, temperature=0);
                   both now also emit impact + urgency
  store.py         SQLite ticket store + per-ticket timeline; seed_if_empty() seeds the queue from the CSV
  sla.py           SLA_TARGETS per priority, due_dates(), sla_risk(), priority_from_matrix() (Impact×Urgency)
  kb.py            KB loader + Retriever (sentence-transformers if installed, else BM25 fallback)
  responder.py     cited L1 reply (Claude streaming via /respond/stream; mock template fallback)
  graph_actions.py Microsoft Graph: create_user/reset_password/add_to_group/assign_license (dry-run gate, password redaction)
  audit.py         append-only audit_events in tickets.db — global cross-ticket record
  static/index.html  single-page workspace UI: queue + ticket detail + intake (English, vanilla JS)
kb/                12 markdown KB articles (KB001..KB012)
data/sample_tickets.csv   60 hand-labelled tickets (gold_* columns) — also seeds the ticket queue
eval/run_eval.py   per-field accuracy + macro-F1; writes eval/last_results.json (gitignored)
docs/              m365-setup.md, keep-warm.md (pitch/demo-script CN notes are local-only, gitignored)
render.yaml        Render blueprint (mock demo)
```

## Key conventions & decisions (gotchas — read before editing)
- **`.env` is gitignored AND takes precedence over OS env vars** (`config.py` → `settings_customise_sources`). So to change config locally, edit `.env`, not the shell. On deploy (no `.env` file), platform env vars apply.
- **Safe defaults:** `USE_MOCK_LLM=true` (rule baseline, no API) and `GRAPH_DRY_RUN=true`. Set `USE_MOCK_LLM=false` + `ANTHROPIC_API_KEY` for real Claude; `GRAPH_DRY_RUN=false` for real Graph (lab tenant only).
- **Models (aliases, no date suffix):** classify = `claude-haiku-4-5`, respond = `claude-sonnet-4-6`. Classifier uses **strict tool-use** + `temperature=0` for reproducible eval.
- **Retrieval:** BM25 (`rank-bm25`) by default; installing `requirements-rag.txt` auto-upgrades to embeddings. KB hit (classifier field) is independent of BM25 retrieval.
- **Graph password reset** needs the app's service principal to hold the **User Administrator** directory role (Graph perms alone give 403). Right after creating a user, reset-by-UPN can 404 (replication lag) — use the object id.
- **Ticket store (`store.py`, SQLite at `tickets.db`, gitignored):** built at import in `main.py` (`init_db()` + `seed_if_empty()`). Seeding uses **`rule_based_classify` directly** (not `classify()`) so first-run/startup never burns the API even when a real key is configured; created_at is back-dated per ticket so SLA risk is a deliberate mix (~50% on-track / 33% at-risk / 17% breached). To get a fresh demo queue, just delete `tickets.db` and restart.
- **Eval continuity:** the classifier still predicts `priority` directly — `impact`/`urgency` are *added* fields. The ITIL **Impact×Urgency→Priority** matrix (`sla.priority_from_matrix`) is shown in the UI as a cross-check only; it does **not** drive the stored priority or eval. Eval set is now **60 tickets** with re-cleaned `kb_hit` gold labels and KB007–KB012 added (see README eval table).
- **Two logs, two jobs:** per-ticket **timeline** lives in SQLite (`ticket_events`); the global **`audit_events`** table (same DB) is the cross-ticket record. Lifecycle mutations write to both. Graph actions accept an optional `ticket_id` to also land on that ticket's timeline.
- **venv** lives at `.venv/`.

## Safety & honesty (do not break)
- **Never commit secrets.** `.env`, `tickets.db*`, `eval/last_results.json`, `.venv/` are gitignored. **Before any push, verify no secret is staged or in history.**
- **Passwords never enter the audit log** (`graph_actions._run` redacts; `generated_password` is returned to the caller only).
- **Lab only:** Graph targets a free, isolated Entra tenant; sample tickets only. Never claim production / real users.
- **The public Render demo runs in mock mode.** The eval numbers below come from the **offline eval + a lab tenant**, NOT the public demo. Don't imply the demo runs Claude or touches a real tenant.

## Eval numbers (reproducible, temperature=0; 60-ticket labelled set)
Keyword baseline → Claude (Haiku 4.5): category **82→85%**, incident-vs-request **82→98%**,
priority **57→78%**, kb_hit **52→87%** (gold re-cleaned + KB expanded), macro-F1 **71→85%**.
Graph live-verified on lab tenant: `create_user 201`, `reset_password 204`, `add_to_group 204`.

## Working efficiently here (for the agent)
- Read this file + `ROADMAP.md` + only the specific file you're changing. Don't re-explore the whole repo.
- After a change: run the relevant check (`python -m eval.run_eval ...` for classifier changes; start the server for UI changes). Commit with a clear message. Push only when asked.
- Keep changes scoped; this is a weekend-MVP portfolio piece — flag scope creep.
