"""贯穿全应用的数据模型（pydantic）。"""
from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    account_access = "account_access"   # 账号 / 登录 / 权限
    hardware = "hardware"               # 笔记本、外设、打印机
    software = "software"               # 应用安装 / 报错
    network = "network"                 # WiFi / VPN / 连接
    email = "email"                     # 邮箱 / Outlook / 分发组
    security = "security"               # 钓鱼 / 可疑活动 / MFA
    other = "other"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketType(StrEnum):
    incident = "incident"   # 坏了 / 出问题
    request = "request"     # 想要 / 申请某项服务


# --- Service Desk 工单生命周期 / ITSM 字段 ---
class TicketStatus(StrEnum):
    new = "new"
    in_progress = "in_progress"
    waiting_user = "waiting_user"
    escalated = "escalated"
    resolved = "resolved"


class Impact(StrEnum):
    """受影响范围：single user → 整个部门/站点。"""
    low = "low"        # 单个用户、有 workaround
    medium = "medium"  # 一组用户 / 单个业务应用
    high = "high"      # 整个部门 / 站点 / 关键系统


class Urgency(StrEnum):
    """多快需要解决。"""
    low = "low"
    medium = "medium"
    high = "high"


class Channel(StrEnum):
    """工单来源渠道。"""
    email = "email"
    phone = "phone"
    portal = "portal"
    chat = "chat"
    walk_in = "walk_in"


class EscalationTeam(StrEnum):
    """升级到的 L2 / 专业组。"""
    l2_endpoint = "l2_endpoint"            # 桌面 / 终端
    l2_apps = "l2_apps"                    # 应用支持
    network = "network"                    # 网络 / VPN
    identity_security = "identity_security"  # 身份 / 安全
    vendor = "vendor"                      # 第三方厂商


class ResolutionCode(StrEnum):
    """关单代码（最后怎么解决的）。"""
    resolved_by_kb = "resolved_by_kb"
    password_reset = "password_reset"
    account_unlocked = "account_unlocked"
    access_granted = "access_granted"
    software_reinstall = "software_reinstall"
    config_change = "config_change"
    hardware_replaced = "hardware_replaced"
    user_education = "user_education"
    no_fault_found = "no_fault_found"
    duplicate = "duplicate"
    workaround_provided = "workaround_provided"
    escalated_to_l2 = "escalated_to_l2"


class Ticket(BaseModel):
    id: str | None = None
    subject: str = ""
    body: str
    requester: str | None = None


class Classification(BaseModel):
    category: Category
    priority: Priority
    ticket_type: TicketType
    # impact / urgency 是新增的预测字段；给默认值以保持向后兼容（eval 不读这两项）。
    impact: Impact = Impact.medium
    urgency: Urgency = Urgency.medium
    kb_hit: str | None = Field(
        default=None, description="ID of the KB article hit (e.g. KB001), or None"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning: str = ""
    source: str = "mock"   # "mock"(规则基线) / "claude" / "claude-fallback"


class TriageItem(BaseModel):
    """A ticket plus its classification (returned by batch endpoints)."""
    ticket: Ticket
    classification: Classification


class Feedback(BaseModel):
    """L1 operator feedback on a reply draft (human-in-the-loop)."""
    ticket_subject: str = ""
    status: str            # "resolved" | "escalate"
    category: str | None = None
    priority: str | None = None
    ticket_id: str | None = None   # 若关联工单，则同时写入该工单 timeline


class Citation(BaseModel):
    id: str
    title: str
    score: float = 0.0


class Reply(BaseModel):
    reply_text: str
    cited_kb: list[str] = []
    source: str = "mock"   # "mock"(模板) 或 "claude"


class TriageResult(BaseModel):
    """Full pipeline result: classification + citations + reply draft."""
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
    ticket_id: str | None = None         # 若关联某工单，则把动作写入该工单 timeline


class ResetPasswordRequest(BaseModel):
    user: str                            # UPN 或对象 id
    new_password: str | None = None      # 留空则自动生成
    force_change: bool = True
    ticket_id: str | None = None


class AddToGroupRequest(BaseModel):
    user: str                            # 用户对象 id
    group: str                           # 组对象 id
    ticket_id: str | None = None


class AssignLicenseRequest(BaseModel):
    user: str                            # UPN 或对象 id
    sku: str                             # skuId（GUID，可用 /graph/skus 查）
    ticket_id: str | None = None


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


# --- 工单状态机 / 持久化记录 / 时间线 ---
class TimelineEvent(BaseModel):
    """工单自身历史里的一条事件（区别于全局 audit_events 表）。"""
    ts: str
    type: str  # e.g. created, triaged, status_change, graph_action, feedback
    actor: str = "L1 Agent"
    summary: str = ""
    detail: dict | None = None


class StoredTicket(BaseModel):
    """一条持久化工单（含分类、生命周期、SLA 计算结果）。"""
    id: str
    subject: str = ""
    body: str = ""
    requester: str | None = None
    channel: Channel = Channel.portal
    assignee: str | None = None
    status: TicketStatus = TicketStatus.new

    # 分类 / 三连
    category: Category = Category.other
    ticket_type: TicketType = TicketType.incident
    impact: Impact = Impact.medium
    urgency: Urgency = Urgency.medium
    priority: Priority = Priority.medium       # 分类器直接给的优先级（eval 口径）
    priority_matrix: Priority | None = None    # Impact×Urgency 矩阵推导出的优先级（ITIL 交叉验证）
    kb_hit: str | None = None
    confidence: float = 0.5

    # 升级 / 解决
    escalation_team: EscalationTeam | None = None
    escalation_reason: str | None = None
    resolution_code: ResolutionCode | None = None
    resolution_notes: str | None = None

    # 时间 / SLA
    created_at: str = ""
    updated_at: str = ""
    resolved_at: str | None = None
    sla_response_due: str | None = None
    sla_resolve_due: str | None = None
    sla_risk: str = "on_track"   # on_track | at_risk | breached | met | missed

    timeline: list[TimelineEvent] = []   # 仅 GET /tickets/{id} 详情时填充


class CreateTicketRequest(BaseModel):
    subject: str = ""
    body: str
    requester: str | None = None
    channel: Channel = Channel.portal


class StatusChangeRequest(BaseModel):
    status: TicketStatus
    note: str | None = None


class EscalateRequest(BaseModel):
    team: EscalationTeam
    reason: str


class ResolveRequest(BaseModel):
    resolution_code: ResolutionCode
    notes: str | None = None


class CommentRequest(BaseModel):
    note: str
    actor: str = "L1 Agent"
