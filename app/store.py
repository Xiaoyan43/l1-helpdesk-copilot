"""SQLite 工单库：持久化工单 + 每工单时间线（timeline）。

和全局 audit_log.jsonl 分工不同：
- audit_log.jsonl（见 audit.py）= 跨工单的横切记录（分类 / Graph 动作 / 反馈）。
- 这里的 ticket_events = 每张工单自己的历史，详情页时间线用。

零额外依赖（标准库 sqlite3）。每次调用开/关一个连接：FastAPI 同步路由跑在线程池里，
连接在各自线程内创建并使用，配合写锁即可安全。
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

from . import sla
from .classifier import rule_based_classify
from .config import get_settings
from .data_io import PROJECT_ROOT, load_tickets_csv
from .models import (
    Category,
    Channel,
    Classification,
    EscalationTeam,
    ResolutionCode,
    StoredTicket,
    Ticket,
    TicketStatus,
    TimelineEvent,
)

_lock = threading.Lock()

# 工单表里的列（顺序即插入顺序）
_COLUMNS = [
    "id", "subject", "body", "requester", "channel", "assignee", "status",
    "category", "ticket_type", "impact", "urgency", "priority", "kb_hit", "confidence",
    "escalation_team", "escalation_reason", "resolution_code", "resolution_notes",
    "created_at", "updated_at", "resolved_at", "sla_response_due", "sla_resolve_due",
]


def _path() -> Path:
    p = Path(get_settings().tickets_db_path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _v(x):
    """枚举取 .value，其余原样（None 保持 None）。"""
    return x.value if isinstance(x, Enum) else x


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                subject TEXT, body TEXT, requester TEXT,
                channel TEXT, assignee TEXT, status TEXT,
                category TEXT, ticket_type TEXT, impact TEXT, urgency TEXT,
                priority TEXT, kb_hit TEXT, confidence REAL,
                escalation_team TEXT, escalation_reason TEXT,
                resolution_code TEXT, resolution_notes TEXT,
                created_at TEXT, updated_at TEXT, resolved_at TEXT,
                sla_response_due TEXT, sla_resolve_due TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                ts TEXT, type TEXT, actor TEXT, summary TEXT, detail_json TEXT
            )
            """
        )


def _row_to_ticket(row: sqlite3.Row, timeline: list[TimelineEvent] | None = None) -> StoredTicket:
    d = dict(row)
    impact, urgency = d["impact"], d["urgency"]
    risk = sla.sla_risk(
        d.get("sla_resolve_due"), d.get("status"),
        created_at=d.get("created_at"), resolved_at=d.get("resolved_at"),
    )
    matrix = sla.priority_from_matrix(impact, urgency) if impact and urgency else None
    return StoredTicket(
        id=d["id"], subject=d["subject"] or "", body=d["body"] or "",
        requester=d["requester"], channel=d["channel"] or Channel.portal.value,
        assignee=d["assignee"], status=d["status"] or TicketStatus.new.value,
        category=d["category"] or Category.other.value,
        ticket_type=d["ticket_type"] or "incident",
        impact=impact or "medium", urgency=urgency or "medium",
        priority=d["priority"] or "medium", priority_matrix=matrix,
        kb_hit=d["kb_hit"], confidence=d["confidence"] if d["confidence"] is not None else 0.5,
        escalation_team=d["escalation_team"], escalation_reason=d["escalation_reason"],
        resolution_code=d["resolution_code"], resolution_notes=d["resolution_notes"],
        created_at=d["created_at"] or "", updated_at=d["updated_at"] or "",
        resolved_at=d["resolved_at"],
        sla_response_due=d["sla_response_due"], sla_resolve_due=d["sla_resolve_due"],
        sla_risk=risk, timeline=timeline or [],
    )


def list_tickets(status: str | None = None) -> list[StoredTicket]:
    q = "SELECT * FROM tickets"
    args: tuple = ()
    if status:
        q += " WHERE status = ?"
        args = (status,)
    q += " ORDER BY datetime(created_at) DESC"
    with _connect() as conn:
        rows = conn.execute(q, args).fetchall()
    return [_row_to_ticket(r) for r in rows]


def get_timeline(ticket_id: str) -> list[TimelineEvent]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_events WHERE ticket_id = ? ORDER BY id DESC", (ticket_id,)
        ).fetchall()
    out = []
    for r in rows:
        detail = json.loads(r["detail_json"]) if r["detail_json"] else None
        out.append(TimelineEvent(ts=r["ts"], type=r["type"], actor=r["actor"] or "",
                                 summary=r["summary"] or "", detail=detail))
    return out


def get_ticket(ticket_id: str) -> StoredTicket | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not row:
        return None
    return _row_to_ticket(row, timeline=get_timeline(ticket_id))


def add_event(ticket_id: str, type: str, summary: str,
              actor: str = "L1 Agent", detail: dict | None = None) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO ticket_events (ticket_id, ts, type, actor, summary, detail_json) "
            "VALUES (?,?,?,?,?,?)",
            (ticket_id, _now(), type, actor, summary,
             json.dumps(detail, ensure_ascii=False) if detail else None),
        )


def next_ticket_id() -> str:
    with _connect() as conn:
        rows = conn.execute("SELECT id FROM tickets").fetchall()
    nums = [int(r["id"][1:]) for r in rows if r["id"] and r["id"][1:].isdigit()]
    return f"T{(max(nums) + 1 if nums else 1):03d}"


def _insert(cols: dict) -> None:
    full = {c: _v(cols.get(c)) for c in _COLUMNS}
    placeholders = ",".join("?" for _ in _COLUMNS)
    with _lock, _connect() as conn:
        conn.execute(
            f"INSERT INTO tickets ({','.join(_COLUMNS)}) VALUES ({placeholders})",
            tuple(full[c] for c in _COLUMNS),
        )


def create_ticket(
    ticket: Ticket, cl: Classification, channel: Channel | str = Channel.portal,
    status: TicketStatus | str = TicketStatus.new,
    created_at: str | None = None, ticket_id: str | None = None, **extra,
) -> StoredTicket:
    """从一张工单 + 分类结果落库（计算 SLA 截止时间）。extra 可覆盖任意列（seeding 用）。"""
    tid = ticket_id or ticket.id or next_ticket_id()
    created = created_at or _now()
    resp_due, res_due = sla.due_dates(created, cl.priority)
    cols = {
        "id": tid, "subject": ticket.subject, "body": ticket.body,
        "requester": ticket.requester, "channel": channel, "assignee": None,
        "status": status,
        "category": cl.category, "ticket_type": cl.ticket_type,
        "impact": cl.impact, "urgency": cl.urgency, "priority": cl.priority,
        "kb_hit": cl.kb_hit, "confidence": cl.confidence,
        "created_at": created, "updated_at": created, "resolved_at": None,
        "sla_response_due": resp_due, "sla_resolve_due": res_due,
    }
    cols.update(extra)
    _insert(cols)
    return get_ticket(tid)


def update_ticket(ticket_id: str, **fields) -> StoredTicket | None:
    fields = {k: _v(v) for k, v in fields.items() if k in _COLUMNS}
    fields["updated_at"] = _now()
    sets = ",".join(f"{k} = ?" for k in fields)
    with _lock, _connect() as conn:
        conn.execute(f"UPDATE tickets SET {sets} WHERE id = ?",
                     (*fields.values(), ticket_id))
    return get_ticket(ticket_id)


# --- Seeding：首次启动把 50 条样本工单铺成一个有生命力的队列 -------------------
_CHANNELS = [Channel.email, Channel.phone, Channel.portal, Channel.chat, Channel.walk_in]

_ESC_TEAM_BY_CAT = {
    Category.account_access: EscalationTeam.identity_security,
    Category.security: EscalationTeam.identity_security,
    Category.network: EscalationTeam.network,
    Category.email: EscalationTeam.l2_apps,
    Category.software: EscalationTeam.l2_apps,
    Category.hardware: EscalationTeam.l2_endpoint,
    Category.other: EscalationTeam.l2_apps,
}
_ESC_REASON_BY_CAT = {
    Category.account_access: "L1 password/unlock steps exhausted; needs User Administrator role at L2 identity.",
    Category.security: "Possible security incident — handing to identity & security for investigation.",
    Category.network: "Beyond L1 (VPN/routing); needs the network team to inspect the gateway.",
    Category.email: "Mail-flow / mailbox config beyond L1 tooling; routing to apps support.",
    Category.software: "Reinstall/repair didn't fix it; app support to check server-side config.",
    Category.hardware: "Hardware fault suspected; dispatching to endpoint/desk-side team.",
    Category.other: "Outside L1 scope after triage; routing to L2 for ownership.",
}
_RES_CODE_BY_CAT = {
    Category.account_access: ResolutionCode.password_reset,
    Category.security: ResolutionCode.user_education,
    Category.network: ResolutionCode.config_change,
    Category.email: ResolutionCode.config_change,
    Category.software: ResolutionCode.software_reinstall,
    Category.hardware: ResolutionCode.hardware_replaced,
    Category.other: ResolutionCode.resolved_by_kb,
}

# idx % 8 → 状态分布（new 偏多，少量 escalated/resolved）
_STATUS_CYCLE = [
    TicketStatus.new, TicketStatus.new, TicketStatus.new,
    TicketStatus.in_progress, TicketStatus.in_progress,
    TicketStatus.waiting_user, TicketStatus.escalated, TicketStatus.resolved,
]


def seed_if_empty() -> int:
    """若工单表为空，则用样本 CSV 铺底。返回插入数量。"""
    with _connect() as conn:
        if conn.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"] > 0:
            return 0

    # 按各自 SLA 解决目标的不同比例回推 created_at，让风险标签有意识地分布：
    # < .75 → on_track，.75–1.0 → at_risk，> 1.0 → breached（resolved 另算）。
    _AGE_FRACTIONS = [0.3, 0.5, 0.7, 0.85, 0.95, 1.2]   # ≈ 50% on_track / 33% at_risk / 17% breached

    tickets = load_tickets_csv()
    now = datetime.now(timezone.utc)
    inserted = 0
    for idx, t in enumerate(tickets):
        cl = rule_based_classify(t)           # 规则基线：离线、确定、不烧 API
        channel = _CHANNELS[idx % len(_CHANNELS)]
        status = _STATUS_CYCLE[idx % len(_STATUS_CYCLE)]
        cat = cl.category
        _, res_min = sla.SLA_TARGETS[cl.priority]
        if status == TicketStatus.resolved:
            age_min = res_min * 2.5           # 足够久远，好让 resolved_at 落在过去
        else:
            age_min = res_min * _AGE_FRACTIONS[(idx * 5) % len(_AGE_FRACTIONS)]
        created = (now - timedelta(minutes=age_min)).isoformat(timespec="seconds")

        extra: dict = {}
        events: list[tuple] = [
            ("created", "requester", f"Ticket created via {channel.value}"),
            ("triaged", "system",
             f"Auto-triaged: {cat.value} / {cl.ticket_type.value} / priority {cl.priority.value} "
             f"(impact {cl.impact.value}, urgency {cl.urgency.value})"),
        ]
        if status in (TicketStatus.in_progress, TicketStatus.waiting_user,
                      TicketStatus.escalated, TicketStatus.resolved):
            extra["assignee"] = "L1 Agent"
            events.append(("status_change", "L1 Agent", "Picked up — work started"))
        if status == TicketStatus.waiting_user:
            events.append(("status_change", "L1 Agent", "Waiting on user — requested more info"))
        if status == TicketStatus.escalated:
            team = _ESC_TEAM_BY_CAT.get(cat, EscalationTeam.l2_apps)
            reason = _ESC_REASON_BY_CAT.get(cat, "Outside L1 scope after triage.")
            extra["escalation_team"] = team
            extra["escalation_reason"] = reason
            events.append(("escalated", "L1 Agent", f"Escalated to {team.value}: {reason}"))
        if status == TicketStatus.resolved:
            code = _RES_CODE_BY_CAT.get(cat, ResolutionCode.resolved_by_kb)
            extra["resolution_code"] = code
            extra["resolution_notes"] = "Resolved at L1 using the KB runbook; confirmed with the user."
            # 一半按时关单(met)，一半略超(missed)，让 SLA 统计有对比
            factor = 0.6 if idx % 2 == 0 else 1.4
            resolved_at = (datetime.fromisoformat(created)
                           + timedelta(minutes=res_min * factor)).isoformat(timespec="seconds")
            extra["resolved_at"] = resolved_at
            extra["updated_at"] = resolved_at
            events.append(("resolved", "L1 Agent", f"Resolved ({code.value})"))

        create_ticket(t, cl, channel=channel, status=status, created_at=created, **extra)
        for etype, actor, summary in events:
            add_event(t.id, etype, summary, actor=actor)
        inserted += 1
    return inserted
