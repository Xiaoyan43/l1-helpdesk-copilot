"""贯穿全应用的数据模型（pydantic）。"""
from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    account_access = "account_access"   # 账号 / 登录 / 权限
    hardware = "hardware"               # 笔记本、外设、打印机
    software = "software"               # 应用安装 / 报错
    network = "network"                 # WiFi / VPN / 连接
    email = "email"                     # 邮箱 / Outlook / 分发组
    security = "security"               # 钓鱼 / 可疑活动 / MFA
    other = "other"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketType(str, Enum):
    incident = "incident"   # 坏了 / 出问题
    request = "request"     # 想要 / 申请某项服务


class Ticket(BaseModel):
    id: str | None = None
    subject: str = ""
    body: str
    requester: str | None = None


class Classification(BaseModel):
    category: Category
    priority: Priority
    ticket_type: TicketType
    kb_hit: str | None = Field(
        default=None, description="命中的 KB 文章 id（如 KB001），无则 None"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning: str = ""
    source: str = "mock"   # "mock"(规则基线) / "claude" / "claude-fallback"


class TriageItem(BaseModel):
    """一条工单 + 它的分类结果（批量接口返回用）。"""
    ticket: Ticket
    classification: Classification


class Citation(BaseModel):
    id: str
    title: str
    score: float = 0.0


class Reply(BaseModel):
    reply_text: str
    cited_kb: list[str] = []
    source: str = "mock"   # "mock"(模板) 或 "claude"


class TriageResult(BaseModel):
    """完整流水线结果：分类 + 检索引用 + 回复草稿。"""
    ticket: Ticket
    classification: Classification
    citations: list[Citation] = []
    reply: Reply
    retriever_mode: str = "bm25"


# --- Microsoft Graph 账号动作（lab 租户） ---
class CreateUserRequest(BaseModel):
    display_name: str
    user_principal_name: str            # 如 maria@yourtenant.onmicrosoft.com
    mail_nickname: str | None = None
    password: str | None = None          # 留空则自动生成强临时密码
    usage_location: str = "US"           # 分配许可前必须有


class ResetPasswordRequest(BaseModel):
    user: str                            # UPN 或对象 id
    new_password: str | None = None      # 留空则自动生成
    force_change: bool = True


class AddToGroupRequest(BaseModel):
    user: str                            # 用户对象 id
    group: str                           # 组对象 id


class AssignLicenseRequest(BaseModel):
    user: str                            # UPN 或对象 id
    sku: str                             # skuId（GUID，可用 /graph/skus 查）


class ActionResult(BaseModel):
    action: str
    dry_run: bool
    success: bool
    summary: str
    request: dict = {}                   # 回显的 Graph 请求（密码已脱敏）
    graph_status: int | None = None
    detail: dict | None = None
    error: str | None = None
    generated_password: str | None = None  # 仅返回给操作员，不写入审计日志
