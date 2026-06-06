"""Microsoft Graph 账号动作（仅对免费 M365 开发者租户）。

四个 L1 常见账号操作：建用户 / 重置密码 / 加入组 / 分配许可。
安全护栏：
- 默认 `GRAPH_DRY_RUN=true`：只构造并返回将要发送的 Graph 请求，不真的调用。
- 凭据缺失时也自动走 dry-run。
- 明文密码：脱敏后才回显/审计；真实临时密码只通过 ActionResult.generated_password
  返回给当前操作员一次。
认证：azure-identity 的 client-credentials（app-only）流。
"""
import copy
import json
import secrets
import string

import httpx

from .audit import log_event
from .config import get_settings
from .models import (
    ActionResult,
    AddToGroupRequest,
    AssignLicenseRequest,
    CreateUserRequest,
    ResetPasswordRequest,
)

GRAPH = "https://graph.microsoft.com/v1.0"
_SYMBOLS = "!@#$%^&*"


def _creds_ready() -> bool:
    s = get_settings()
    return bool(s.azure_tenant_id and s.azure_client_id and s.azure_client_secret)


def _token() -> str:
    from azure.identity import ClientSecretCredential

    s = get_settings()
    assert s.azure_tenant_id and s.azure_client_id and s.azure_client_secret
    cred = ClientSecretCredential(s.azure_tenant_id, s.azure_client_id, s.azure_client_secret)
    return cred.get_token("https://graph.microsoft.com/.default").token


def gen_password(length: int = 16) -> str:
    """生成满足 Entra 复杂度的强临时密码。"""
    alphabet = string.ascii_letters + string.digits + _SYMBOLS
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd) and any(c in _SYMBOLS for c in pwd)):
            return pwd


def _redact(body: dict) -> dict:
    b = copy.deepcopy(body or {})
    pp = b.get("passwordProfile")
    if isinstance(pp, dict) and "password" in pp:
        pp["password"] = "***REDACTED***"
    if "password" in b:
        b["password"] = "***REDACTED***"
    return b


def _run(action: str, method: str, path: str, body: dict | None,
         summary: str, secret: str | None = None) -> ActionResult:
    s = get_settings()
    url = f"{GRAPH}{path}"
    safe_body = _redact(body or {})

    if s.graph_dry_run or not _creds_ready():
        res = ActionResult(
            action=action, dry_run=True, success=True, summary=summary,
            request={"method": method, "url": url, "body": safe_body},
            generated_password=secret,
        )
    else:
        try:
            with httpx.Client(timeout=30.0) as c:
                r = c.request(
                    method, url,
                    headers={"Authorization": f"Bearer {_token()}",
                             "Content-Type": "application/json"},
                    json=body if body else None,
                )
            ok = r.status_code in (200, 201, 204)
            ctype = r.headers.get("content-type", "")
            payload = r.json() if (r.content and ctype.startswith("application/json")) else {}
            res = ActionResult(
                action=action, dry_run=False, success=ok, summary=summary,
                request={"method": method, "url": url, "body": safe_body},
                graph_status=r.status_code,
                detail=payload if ok else None,
                error=None if ok else json.dumps(payload, ensure_ascii=False)[:500],
                generated_password=secret if ok else None,
            )
        except Exception as e:  # 网络/认证异常
            res = ActionResult(
                action=action, dry_run=False, success=False, summary=summary,
                request={"method": method, "url": url, "body": safe_body},
                error=str(e),
            )

    audit = res.model_dump()
    audit.pop("generated_password", None)   # 绝不审计明文密码
    log_event("graph_action", **audit)
    return res


# --- 四个账号动作 ---
def create_user(req: CreateUserRequest) -> ActionResult:
    pwd = req.password or gen_password()
    body = {
        "accountEnabled": True,
        "displayName": req.display_name,
        "mailNickname": req.mail_nickname or req.user_principal_name.split("@")[0],
        "userPrincipalName": req.user_principal_name,
        "usageLocation": req.usage_location,
        "passwordProfile": {"forceChangePasswordNextSignIn": True, "password": pwd},
    }
    return _run("create_user", "POST", "/users", body,
                f"create user {req.user_principal_name}", secret=pwd)


def reset_password(req: ResetPasswordRequest) -> ActionResult:
    pwd = req.new_password or gen_password()
    body = {"passwordProfile": {
        "forceChangePasswordNextSignIn": req.force_change, "password": pwd}}
    return _run("reset_password", "PATCH", f"/users/{req.user}", body,
                f"reset password for {req.user}", secret=pwd)


def add_to_group(req: AddToGroupRequest) -> ActionResult:
    body = {"@odata.id": f"{GRAPH}/directoryObjects/{req.user}"}
    return _run("add_to_group", "POST", f"/groups/{req.group}/members/$ref", body,
                f"add user {req.user} to group {req.group}")


def assign_license(req: AssignLicenseRequest) -> ActionResult:
    body = {"addLicenses": [{"skuId": req.sku, "disabledPlans": []}], "removeLicenses": []}
    return _run("assign_license", "POST", f"/users/{req.user}/assignLicense", body,
                f"assign license {req.sku} to {req.user}")


# --- 只读辅助（发现租户里的 id；需真实凭据） ---
def _get(path: str) -> dict:
    if not _creds_ready():
        return {"note": "Configure Graph credentials in .env to read live tenant data."}
    with httpx.Client(timeout=30.0) as c:
        r = c.get(f"{GRAPH}{path}", headers={"Authorization": f"Bearer {_token()}"})
    try:
        return r.json()
    except Exception:
        return {"status": r.status_code, "text": r.text[:500]}


def list_users(top: int = 15) -> dict:
    return _get(f"/users?$select=id,displayName,userPrincipalName&$top={top}")


def list_groups(top: int = 30) -> dict:
    return _get(f"/groups?$select=id,displayName&$top={top}")


def list_skus() -> dict:
    return _get("/subscribedSkus?$select=skuId,skuPartNumber,prepaidUnits,consumedUnits")
