# KB012 — Common application issues (Teams, Zoom, crashes)

**Applies to:** Microsoft Teams, Zoom, desktop apps that hang/crash, post-update breakage.

## Symptoms
- Teams stuck on loading screen; meetings won't connect audio/video.
- Zoom "connection error" despite working internet.
- Desktop app crashes on startup (after update or without clear cause).

## L1 resolution steps
1. Confirm whether web version works (Teams web, Outlook web) to isolate client vs service.
2. Sign out and quit the app fully; clear cache folders per vendor KB if issue persists.
3. Repair or reinstall the app from the managed software portal (Company Portal / Intune).
4. For Zoom/Teams AV issues: check OS privacy settings (mic/camera), VPN split-tunnel, and firewall prompts.
5. Retest launch and a short test meeting/call before closing the ticket.

## When to escalate
- Line-of-business app outage affecting a whole team (e.g., payroll) → escalate to Apps/L2 owner — not covered by this article.
- Crash persists after clean reinstall → L2 Apps or vendor support with logs.
