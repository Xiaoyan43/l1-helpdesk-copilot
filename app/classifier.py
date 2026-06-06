"""工单分类。

两条路径：
- 规则基线 `rule_based_classify`：零依赖、离线可用，既能 demo，也是评测里的 baseline。
- Claude 分类 `llm_classify`：阶段 1 接入（现在先占位）。

`classify()` 按 settings.use_mock_llm 分流。
"""
from anthropic import Anthropic

from .config import get_settings
from .models import (
    Category,
    Classification,
    Impact,
    Priority,
    Ticket,
    TicketType,
    Urgency,
)

# KB 目录：id -> 标题。分类提示词 + 阶段2 的 RAG 都会用到（届时和 kb/ 下文件对齐）。
KB_CATALOG: dict[str, str] = {
    "KB001": "Password reset & account unlock",
    "KB002": "VPN & WiFi connectivity",
    "KB003": "Email / Outlook / distribution & shared mailboxes",
    "KB004": "Software install & licensing",
    "KB005": "Hardware (laptop / monitor / printer / peripherals)",
    "KB006": "Security: phishing & suspicious activity",
}

# --- 关键词表（规则基线用，刻意保持简单） ---
_CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.account_access: ["password", "login", "log in", "account", "locked",
                              "access", "mfa", "reset", "unlock", "sign in"],
    Category.network: ["vpn", "wifi", "wi-fi", "network", "internet", "connect",
                       "disconnect", "ethernet"],
    Category.email: ["email", "outlook", "mailbox", "distribution list", "spam",
                     "calendar", "smtp"],
    Category.hardware: ["laptop", "monitor", "keyboard", "mouse", "printer",
                        "docking", "battery", "screen", "device"],
    Category.software: ["install", "license", "app", "application", "software",
                        "update", "teams", "excel", "crash"],
    Category.security: ["phishing", "suspicious", "malware", "virus", "breach",
                        "hacked", "compromise"],
}

_REQUEST_HINTS = ["please", "request", "need", "would like", "set up", "create",
                  "new hire", "onboard", "add me", "grant", "provision"]
_INCIDENT_HINTS = ["not working", "can't", "cannot", "won't", "down", "error",
                   "broken", "failed", "stuck", "issue", "problem"]

_CRITICAL_HINTS = ["breach", "hacked", "compromise", "outage", "everyone", "whole office",
                   "all users", "ransomware"]
_HIGH_HINTS = ["urgent", "asap", "locked out", "can't work", "deadline", "ceo",
               "executive", "vpn down", "phishing"]

# impact / urgency 的规则线索（保持简单；不影响 eval 字段）
_HIGH_IMPACT_HINTS = ["everyone", "all users", "whole office", "entire office", "whole site",
                      "department", "nobody can", "no one can", "company-wide", "multiple users",
                      "several people", "all staff", "the whole team", "site down"]
_LOW_URGENCY_HINTS = ["not urgent", "no rush", "when you get a chance", "whenever", "low priority",
                      "no hurry", "at your convenience", "sometime", "no immediate"]

# 类别 -> KB 文章 id（阶段 2 会和真实 KB 对齐）
_KB_MAP: dict[Category, str] = {
    Category.account_access: "KB001",
    Category.network: "KB002",
    Category.email: "KB003",
    Category.software: "KB004",
    Category.hardware: "KB005",
    Category.security: "KB006",
}


def rule_based_classify(ticket: Ticket) -> Classification:
    text = f"{ticket.subject}\n{ticket.body}".lower()

    # 类别：命中关键词最多者
    scores = {
        cat: sum(text.count(kw) for kw in kws)
        for cat, kws in _CATEGORY_KEYWORDS.items()
    }
    best_cat, best_score = max(scores.items(), key=lambda kv: kv[1])
    category = best_cat if best_score > 0 else Category.other

    # incident vs request
    req = sum(text.count(h) for h in _REQUEST_HINTS)
    inc = sum(text.count(h) for h in _INCIDENT_HINTS)
    ticket_type = TicketType.request if req >= inc and req > 0 else TicketType.incident

    # 优先级
    if any(h in text for h in _CRITICAL_HINTS):
        priority = Priority.critical
    elif any(h in text for h in _HIGH_HINTS) or category == Category.security:
        priority = Priority.high
    elif category == Category.other:
        priority = Priority.low
    else:
        priority = Priority.medium

    kb_hit = _KB_MAP.get(category) if best_score > 0 else None
    confidence = 0.4 if category == Category.other else min(0.9, 0.5 + 0.1 * best_score)

    # urgency：高/紧急线索→high；明确不急或纯请求→low；其余 medium
    if any(h in text for h in _CRITICAL_HINTS) or any(h in text for h in _HIGH_HINTS):
        urgency = Urgency.high
    elif any(h in text for h in _LOW_URGENCY_HINTS) or (
        ticket_type == TicketType.request and inc == 0
    ):
        urgency = Urgency.low
    else:
        urgency = Urgency.medium

    # impact：影响范围线索→high；常规请求→low；其余 medium
    if any(h in text for h in _HIGH_IMPACT_HINTS) or any(h in text for h in _CRITICAL_HINTS):
        impact = Impact.high
    elif ticket_type == TicketType.request:
        impact = Impact.low
    else:
        impact = Impact.medium

    return Classification(
        category=category,
        priority=priority,
        ticket_type=ticket_type,
        impact=impact,
        urgency=urgency,
        kb_hit=kb_hit,
        confidence=round(confidence, 2),
        reasoning="Rule baseline: keyword counts.",
        source="mock",
    )


# --- Claude 结构化分类（用 tool use 强制结构化输出） ---
_CLASSIFY_TOOL = {
    "name": "record_classification",
    "description": "记录一条 IT 支持工单的结构化分类结果。",
    "strict": True,   # 严格模式：保证输出符合 schema（枚举不会越界）。Haiku 4.5 支持。
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": [c.value for c in Category]},
            "priority": {"type": "string", "enum": [p.value for p in Priority]},
            "ticket_type": {"type": "string", "enum": [t.value for t in TicketType]},
            "impact": {
                "type": "string",
                "enum": [i.value for i in Impact],
                "description": "Business impact: low=single user with a workaround; "
                               "medium=a group of users or one business application; "
                               "high=a whole department/site or a business-critical system.",
            },
            "urgency": {
                "type": "string",
                "enum": [u.value for u in Urgency],
                "description": "How quickly it must be resolved (deadline / degree of disruption).",
            },
            "kb_hit": {
                "type": "string",
                "description": "最匹配的 KB id（如 KB001）；若无文章契合则填 'NONE'。",
            },
            "confidence": {"type": "number"},
            "reasoning": {"type": "string", "description": "一句话分类理由。"},
        },
        # strict 模式要求所有属性都在 required 且禁止额外属性
        "required": ["category", "priority", "ticket_type", "impact", "urgency",
                     "kb_hit", "confidence", "reasoning"],
        "additionalProperties": False,
    },
}

_SYSTEM_TEMPLATE = (
    "You are an L1 IT help desk triage assistant. Classify the ticket and call the "
    "record_classification tool.\n\n"
    "ticket_type: 'incident' = something is broken / not working; "
    "'request' = the user wants a new service, access, item, or change.\n\n"
    "Priority rubric (apply strictly):\n"
    "- critical: many users / a whole site or system down, OR an active account "
    "compromise (account sending spam, confirmed credential theft).\n"
    "- high: a single user is COMPLETELY blocked with no workaround (laptop dead, fully "
    "locked out, can't boot), OR an explicit hard deadline (meeting/presentation within "
    "~1 hour), OR a security report (phishing email, suspicious sign-in).\n"
    "- medium: service is degraded or one app/resource is affected but the user can still "
    "work or has a workaround (VPN drops intermittently, an app crashes, slow WiFi, "
    "printer issue, can't reach one drive, license/sync problem).\n"
    "- low: minor annoyance or routine / non-urgent request (request a monitor or license, "
    "add to a group, set out-of-office, tighten spam filter, or anything marked 'not urgent').\n\n"
    "Calibration examples (NOT the tickets to classify):\n"
    "- 'My laptop is completely dead, I can't work at all' -> high\n"
    "- 'Email is slow to send today but it still works' -> medium\n"
    "- 'Please order me a desk riser when you get a chance' -> low\n"
    "- 'Nobody in the office can reach any system' -> critical\n\n"
    "Also set impact and urgency independently (these drive the ITIL impact x urgency view):\n"
    "- impact: low = one user with a workaround; medium = a group of users or a single "
    "business app; high = a whole department/site or a business-critical system.\n"
    "- urgency: low = routine / no deadline; medium = work is degraded; high = user is "
    "blocked now or there is a hard deadline.\n\n"
    "Set kb_hit to the single best-matching KB id, or 'NONE' if no article fits.\n\n"
    "Knowledge base:\n{catalog}"
)

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=get_settings().anthropic_api_key)
    return _client


def llm_classify(ticket: Ticket) -> Classification:
    """调用 Claude（tool use, strict）做结构化分类；解析失败则回落到规则基线。

    注：未加 prompt caching——system+tools 前缀仅几百 token，低于 Haiku 4.5 的
    4096 token 最小可缓存阈值，加 cache_control 也不会命中（纯开销）。
    """
    s = get_settings()
    catalog = "\n".join(f"{kid}: {title}" for kid, title in KB_CATALOG.items())
    resp = _get_client().messages.create(
        model=s.classify_model,
        max_tokens=400,
        temperature=0,   # 分类要可复现；Haiku 4.5 支持 temperature
        system=_SYSTEM_TEMPLATE.format(catalog=catalog),
        tools=[_CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "record_classification"},
        messages=[{
            "role": "user",
            "content": f"Subject: {ticket.subject}\n\nBody:\n{ticket.body}",
        }],
    )
    data = next(
        (b.input for b in resp.content
         if b.type == "tool_use" and b.name == "record_classification"),
        None,
    )
    if not data:
        fb = rule_based_classify(ticket)
        fb.source = "claude-fallback"
        return fb

    kb = data.get("kb_hit")
    if kb in (None, "", "NONE", "none"):
        kb = None
    try:
        return Classification(
            category=data["category"],
            priority=data["priority"],
            ticket_type=data["ticket_type"],
            impact=data.get("impact", "medium"),
            urgency=data.get("urgency", "medium"),
            kb_hit=kb,
            confidence=float(data.get("confidence", 0.6)),
            reasoning=data.get("reasoning", ""),
            source="claude",
        )
    except Exception:  # 枚举越界等 → 回落
        fb = rule_based_classify(ticket)
        fb.source = "claude-fallback"
        return fb


def classify(ticket: Ticket) -> Classification:
    settings = get_settings()
    if settings.use_mock_llm or not settings.anthropic_api_key:
        return rule_based_classify(ticket)
    return llm_classify(ticket)
