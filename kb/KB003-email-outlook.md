# KB003 — Email / Outlook / distribution & shared mailboxes

**Applies to:** Outlook (desktop & web), Exchange Online, distribution groups, shared mailboxes.

## Symptoms
- Outlook desktop not syncing while webmail works.
- Need access to a shared mailbox or to join/leave a distribution group.

## L1 resolution steps
1. For sync issues, confirm webmail (https://outlook.office.com) shows the missing mail — isolates client vs server.
2. In Outlook desktop: Send/Receive → Update Folder; if stuck, restart Outlook.
3. If still broken, repair the Office profile or recreate the mail profile (Control Panel → Mail).
4. For **shared mailbox / distribution group** access, treat as a *request*: confirm approval from the resource owner, then grant membership/permissions in the admin center.
5. Verify the mailbox auto-maps in Outlook after permissions propagate (can take up to ~60 min).

## When to escalate
- Mail flow problems affecting many users (NDRs, queue backup) → escalate to Messaging team.
