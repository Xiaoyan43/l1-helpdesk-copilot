# AGENTS.md — L1 Help Desk Copilot

> Cross-tool agent instructions (Cursor, Claude Code, Codex, etc.). Mirrors the Claude Code memory.

**Source of truth:** read **[`CLAUDE.md`](CLAUDE.md)** (project memory — architecture, conventions, status) and **[`ROADMAP.md`](ROADMAP.md)** (upgrade backlog) before starting any task, then follow them. Update `ROADMAP.md` as you ship.

## Hard guardrails (do not break)
- **Never commit secrets.** `.env`, `audit_log.jsonl`, `tickets.db*`, `.venv/`, `eval/last_results.json` are gitignored — verify nothing sensitive is staged before any push.
- **Safe defaults:** mock LLM + Microsoft Graph **dry-run**. Lab Entra tenant + sample data only — **never claim production / real users**.
- **Passwords never enter the audit log.**
- Keep changes **scoped** (portfolio MVP); flag scope creep; **push only when asked**.

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload          # UI: http://127.0.0.1:8000/  · API: /docs
python -m eval.run_eval --engine both  # baseline vs Claude on the 50-ticket set
```

## Links
- Repo: https://github.com/Xiaoyan43/l1-helpdesk-copilot
- Live demo (mock mode): https://l1-helpdesk-copilot.onrender.com
