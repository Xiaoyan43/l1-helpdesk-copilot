# KB001 — Password reset & account unlock

**Applies to:** Microsoft 365 / Entra ID accounts, Windows sign-in.

## Symptoms
- "Your account is locked" or repeated sign-in failures.
- Forgotten password; cannot access laptop, email, or VPN.

## L1 resolution steps
1. Verify the user's identity per the help desk identity-check policy (callback or manager confirmation).
2. Ask the user to try **Self-Service Password Reset** at https://aka.ms/sspr first.
3. If locked out, unlock the account in the admin center (Users → select user → Unblock sign-in).
4. If a reset is needed, issue a temporary password and require change at next sign-in.
5. Confirm the user can sign in to https://portal.office.com after the reset.

## Self-service
Encourage users to register for SSPR and MFA so future resets need no ticket.

## When to escalate
- Account shows unfamiliar sign-in locations → treat as possible compromise, see **KB006**.
- Repeated lockouts within an hour → escalate to Identity team (possible stale cached credential).
