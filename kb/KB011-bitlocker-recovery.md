# KB011 — BitLocker recovery key

**Applies to:** Windows BitLocker drive encryption, recovery screen at boot.

## Symptoms
- Laptop stuck at "BitLocker recovery" asking for a 48-digit recovery key.
- Recovery prompt after hardware change, BIOS update, or motherboard replacement.

## L1 resolution steps
1. Verify the user's identity per the help desk identity-check policy (manager callback for lost devices).
2. Look up the BitLocker recovery key in the Microsoft 365 admin center (Devices → select device → Recovery keys) or Entra ID blade.
3. Provide the key to the user securely (phone callback — never email the full key unencrypted).
4. After unlock, confirm Windows boots normally; remind user to sync recovery key backup if policy requires.
5. If key is not found, check legacy escrow (on-prem AD) before escalating.

## When to escalate
- No recovery key on file → Endpoint team (possible reimage / data loss discussion).
- Device reported lost/stolen → Security incident before unlocking (see **KB006**).
