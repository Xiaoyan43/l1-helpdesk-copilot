# KB006 — Security: phishing & suspicious activity

**Applies to:** Suspected phishing emails, account compromise, MFA prompts the user didn't trigger.

## Symptoms
- Email impersonating IT/HR asking to "verify your password" via a link.
- Unexpected MFA prompts; unfamiliar sign-in locations.

## L1 resolution steps
1. **Do not** click links or enter credentials. If the user already did, treat as compromise immediately.
2. Have the user report the message with the **Report Phishing** button (or forward to the security mailbox), then delete it.
3. If credentials may have been entered: reset the password now and revoke active sessions (see **KB001**).
4. For unexpected MFA prompts the user didn't start, instruct them to **Deny** and report it.
5. Record the sender, time, and any link domain in the ticket for the security team.

## When to escalate
- Any confirmed or suspected credential entry / account compromise → escalate to Security immediately (priority high/critical).
- Multiple users report the same campaign → escalate as a potential targeted phishing wave.
