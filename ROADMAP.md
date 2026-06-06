# ROADMAP — L1 Help Desk Copilot

Backlog of upgrades. Tags: **[impact]** low/med/high · **[effort]** S/M/L.
This is a portfolio/lab MVP — keep changes scoped; flag scope creep.

> **Recently shipped (Phase 6 — Service Desk workspace):** SQLite ticket store + timeline
> (`store.py`), queue/detail UI, status lifecycle, Impact×Urgency→Priority + computed SLA risk
> (`sla.py`), escalation reason + L2 team, resolution codes. The `tickets.db` store now exists, so
> "persist audit to SQLite" below is a smaller lift (move the jsonl audit into the same DB).

## ⭐ Suggested next 3 (best portfolio ROf)
1. ~~**Tests + CI**~~ — **done:** pytest (classifier baseline, KB retrieval, Graph dry-run, audit redaction) + GitHub Actions (`ruff` + pytest) + README badge. [high][M]
2. ~~**README hero screenshot**~~ — **done:** `docs/img/workspace-hero.png` embedded at the top of README (queue view with SLA + lifecycle chips). [med][S]
3. ~~**Grow + clean the eval set**~~ — **done:** KB expanded to 12 articles (KB007–KB012); `kb_hit` gold labels re-cleaned; eval set grown to 60 tickets. Claude kb_hit **87%** on re-run. [high][M]

## Quality / accuracy
- [x] Expand KB to 10–12 articles (cover shared-drive/permissions, MFA reset, device perf, license/activation). [med][M]
- [x] Re-clean `kb_hit` gold labels for a consistent NONE-vs-article rule. [med][S]
- [ ] Category few-shot calibration — **use fresh examples, NOT test-set tickets** (avoid overfitting the 50-set). [med][S]
- [ ] Try a stronger classify model (sonnet/opus) and report cost↔accuracy trade-off. [low][S]
- [ ] Per-category precision/recall table in eval output; consider bootstrap CIs. [med][M]
- [ ] Grow test set beyond 50; ideally a 2nd annotator → inter-annotator agreement (more credible number). [high][L]

## Features
- [ ] Streaming reply in the UI (Claude streaming, token-by-token). [med][M]
- [ ] More Graph actions: disable/offboard user, list group members, set manager; assign_license on a licensed trial tenant. [med][M]
- [ ] Smarter suggested-action auto-fill (parse "new hire Maria Chen" → prefill create_user fields). [low][S]
- [ ] Batch view: CSV upload → results table in the UI. [low][M]
- [ ] Persist audit to SQLite/Postgres for the deployed version (jsonl is ephemeral on Render). [med][M]

## Engineering / hardening
- [x] pytest suite (rule baseline, retriever, graph dry-run + redaction, audit). [high][M]
- [x] GitHub Actions CI (ruff lint + pytest on push) + status badge. [high][S]
- [ ] Dockerfile (reproducible / alternative deploy). [low][S]
- [ ] ruff + mypy + pre-commit. [low][S]
- [ ] Prompt caching — only worthwhile once system+tools exceed the cacheable min (~4096 tok for Haiku); currently below it, so skipped on purpose. Revisit if prompts grow. [low][S]
- [ ] Rate limiting on the public demo IF it ever runs real Claude (cost/abuse guard). [med][S]

## Polish / ops
- [ ] Translate code comments + `docs/pitch.md` / `docs/demo-script.md` to English, OR remove those CN prep docs from the public repo (they're personal notes). [low][S]
- [ ] Keep-warm pinger for the free demo (e.g. cron-job.org → `/healthz` every ~14 min) so HR doesn't hit the ~30–60s cold start. [low][S]
- [ ] Optionally run the live demo on real Claude: add `ANTHROPIC_API_KEY` in Render + set `USE_MOCK_LLM=false` (set an Anthropic monthly spend cap first). Keep `GRAPH_DRY_RUN=true` in public. [med][S]

## Out of scope (intentionally NOT doing — MVP discipline)
- Multi-user auth / accounts.
- Real ticketing-system integration (ServiceNow/Jira/Zendesk).
- Vector DB (overkill for ~10 short KB articles — BM25/in-memory is enough).
- Production hardening / SLAs / on-call.
