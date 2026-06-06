# ROADMAP — L1 Help Desk Copilot

Backlog of upgrades. Tags: **[impact]** low/med/high · **[effort]** S/M/L.
This is a portfolio/lab MVP — keep changes scoped; flag scope creep.

> **Recently shipped (Phase 6 — Service Desk workspace):** SQLite ticket store + timeline
> (`store.py`), queue/detail UI, status lifecycle, Impact×Urgency→Priority + computed SLA risk
> (`sla.py`), escalation reason + L2 team, resolution codes. The `tickets.db` store now exists, so
> "persist audit to SQLite" below is a smaller lift (move the jsonl audit into the same DB).

## ⭐ Suggested next 3 (best portfolio ROI)
1. ~~**Keep-warm pinger**~~ — **done:** [`docs/keep-warm.md`](docs/keep-warm.md) — cron-job.org → `/healthz` every ~14 min; linked from README. [low][S]
2. ~~**Eval per-category P/R table**~~ — **done:** `eval/run_eval.py` prints precision / recall / F1 / support per category; saved in `last_results.json`. [med][M]
3. ~~**Streaming reply in UI**~~ — **done:** `/tickets/{id}/respond/stream` (SSE) + token-by-token display in the copilot panel (mock word-chunk or Claude stream). [med][M]

## Previously shipped (prior ⭐3)
1. ~~**Tests + CI**~~ — pytest + GitHub Actions + README badge. [high][M]
2. ~~**README hero screenshot**~~ — `docs/img/workspace-hero.png`. [med][S]
3. ~~**Grow + clean the eval set**~~ — KB007–KB012, 60 tickets, kb_hit re-cleaned. [high][M]

## Quality / accuracy
- [x] Expand KB to 10–12 articles (cover shared-drive/permissions, MFA reset, device perf, license/activation). [med][M]
- [x] Re-clean `kb_hit` gold labels for a consistent NONE-vs-article rule. [med][S]
- [ ] Category few-shot calibration — **use fresh examples, NOT test-set tickets** (avoid overfitting the 50-set). [med][S]
- [ ] Try a stronger classify model (sonnet/opus) and report cost↔accuracy trade-off. [low][S]
- [x] Per-category precision/recall table in eval output; consider bootstrap CIs. [med][M]
- [ ] Grow test set beyond 50; ideally a 2nd annotator → inter-annotator agreement (more credible number). [high][L]

## Features
- [x] Streaming reply in the UI (Claude streaming, token-by-token). [med][M]
- [ ] More Graph actions: disable/offboard user, list group members, set manager; assign_license on a licensed trial tenant. [med][M]
- [x] Smarter suggested-action auto-fill (parse "new hire Maria Chen" → prefill create_user fields). [low][S]
- [ ] Batch view: CSV upload → results table in the UI. [low][M]
- [x] Persist audit to SQLite/Postgres for the deployed version (jsonl is ephemeral on Render). [med][M]

## Engineering / hardening
- [x] pytest suite (rule baseline, retriever, graph dry-run + redaction, audit). [high][M]
- [x] GitHub Actions CI (ruff lint + pytest on push) + status badge. [high][S]
- [x] Dockerfile (reproducible / alternative deploy). [low][S]
- [x] ruff + mypy + pre-commit. [low][S]
- [ ] Prompt caching — only worthwhile once system+tools exceed the cacheable min (~4096 tok for Haiku); currently below it, so skipped on purpose. Revisit if prompts grow. [low][S]
- [ ] Rate limiting on the public demo IF it ever runs real Claude (cost/abuse guard). [med][S]

## Polish / ops
- [ ] Translate code comments + `docs/pitch.md` / `docs/demo-script.md` to English, OR remove those CN prep docs from the public repo (they're personal notes). [low][S]
- [x] Keep-warm pinger for the free demo (e.g. cron-job.org → `/healthz` every ~14 min) so HR doesn't hit the ~30–60s cold start. [low][S]
- [ ] Optionally run the live demo on real Claude: add `ANTHROPIC_API_KEY` in Render + set `USE_MOCK_LLM=false` (set an Anthropic monthly spend cap first). Keep `GRAPH_DRY_RUN=true` in public. [med][S]

## Out of scope (intentionally NOT doing — MVP discipline)
- Multi-user auth / accounts.
- Real ticketing-system integration (ServiceNow/Jira/Zendesk).
- Vector DB (overkill for ~10 short KB articles — BM25/in-memory is enough).
- Production hardening / SLAs / on-call.
