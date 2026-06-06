# KB008 — MFA & Microsoft Authenticator setup

**Applies to:** Microsoft Entra MFA, Authenticator app, new phone / device registration.

## Symptoms
- New phone — can't approve sign-in prompts; Authenticator not set up.
- "MFA not working" or "can't complete verification."
- Lost phone and need MFA re-registration.

## L1 resolution steps
1. Verify the user's identity per the help desk identity-check policy.
2. In the admin center, confirm MFA is enforced and check sign-in logs for failed MFA attempts.
3. Guide the user through **https://aka.ms/mfasetup** to register Authenticator on the new device.
4. If the old device is lost, reset MFA methods for the user, then have them register again at next sign-in.
5. Confirm successful sign-in to https://portal.office.com and VPN (if applicable).

## Self-service
Users with a working secondary MFA method can add a device at https://aka.ms/mfasetup without a ticket.

## When to escalate
- User cannot pass identity verification → escalate to Identity team.
- Repeated MFA failures after re-registration → check Conditional Access policies (Identity team).
