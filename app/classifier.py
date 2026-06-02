"""工单分类。

两条路径：
- 规则基线 `rule_based_classify`：零依赖、离线可用，既能 demo，也是评测里的 baseline。
- Claude 分类 `llm_classify`：阶段 1 接入（现在先占位）。

`classify()` 按 settings.use_mock_llm 分流。
"""
from .config import get_settings
from .models import Category, Classification, Priority, Ticket, TicketType

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

    return Classification(
        category=category,
        priority=priority,
        ticket_type=ticket_type,
        kb_hit=kb_hit,
        confidence=round(confidence, 2),
        reasoning="规则基线：基于关键词计数。",
        source="mock",
    )


def llm_classify(ticket: Ticket) -> Classification:
    """阶段 1 接入 Claude 结构化分类。"""
    raise NotImplementedError("阶段 1 实现：调用 Anthropic SDK 做结构化分类。")


def classify(ticket: Ticket) -> Classification:
    settings = get_settings()
    if settings.use_mock_llm or not settings.anthropic_api_key:
        return rule_based_classify(ticket)
    return llm_classify(ticket)
