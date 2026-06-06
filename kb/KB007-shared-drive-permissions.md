# KB007 — Shared drives & file permissions

**Applies to:** OneDrive, SharePoint, departmental shared folders, network drives.

## Symptoms
- "Access denied" on a shared drive or folder the user could open before.
- Request for read/write access to a project or department share.
- User moved teams and lost access to a shared location.

## L1 resolution steps
1. Confirm the exact path or SharePoint site/library and the error message.
2. Verify the user's identity and that their manager approves access (per data-classification policy).
3. Check group membership for the share's security group in Entra / Active Directory.
4. Grant access via the correct group (preferred) or direct ACL if policy allows; avoid one-off exceptions.
5. Ask the user to sign out/in or wait ~15 minutes for token refresh, then retest.

## When to escalate
- Share contains confidential/finance data and requester lacks approval → route to data owner.
- Permissions look correct but access still fails → escalate to Identity or Storage team (sync/ACL replication).
