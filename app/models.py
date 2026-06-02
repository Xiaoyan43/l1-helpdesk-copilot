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
    source: str = "mock"   # "mock"(规则基线) 或 "claude"
