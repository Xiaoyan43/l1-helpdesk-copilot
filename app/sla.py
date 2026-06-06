"""SLA 目标 + 风险计算 + Impact×Urgency 优先级矩阵。

刻意简化的 lab 模型：用「自工单创建起的固定挂钟分钟数」算 SLA 截止时间，
不考虑工作时间/营业日历（那属于 out of scope）。所有时间戳用 UTC ISO 字符串。
"""
from datetime import datetime, timedelta, timezone

from .models import Impact, Priority, TicketStatus, Urgency

# 每个优先级的 SLA 目标：(首次响应分钟, 解决分钟)
SLA_TARGETS: dict[Priority, tuple[int, int]] = {
    Priority.critical: (15, 4 * 60),     # 15m / 4h
    Priority.high: (30, 8 * 60),         # 30m / 8h
    Priority.medium: (4 * 60, 24 * 60),  # 4h / 24h
    Priority.low: (8 * 60, 72 * 60),     # 8h / 72h
}

# 当已过去 >= 解决目标的这个比例且仍未解决 → at_risk
_AT_RISK_FRACTION = 0.75


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def due_dates(created_at: str, priority: Priority) -> tuple[str, str]:
    """返回 (响应截止, 解决截止) 的 ISO 字符串。"""
    start = _parse(created_at) or datetime.now(timezone.utc)
    resp_min, res_min = SLA_TARGETS.get(priority, SLA_TARGETS[Priority.medium])
    response_due = (start + timedelta(minutes=resp_min)).isoformat(timespec="seconds")
    resolve_due = (start + timedelta(minutes=res_min)).isoformat(timespec="seconds")
    return response_due, resolve_due


def sla_risk(
    resolve_due: str | None,
    status: TicketStatus | str,
    created_at: str | None = None,
    resolved_at: str | None = None,
    now: datetime | None = None,
) -> str:
    """计算 SLA 风险标签。

    已解决：met（按时）/ missed（超时）。
    进行中：on_track / at_risk（已过 75% 时限）/ breached（已超时）。
    """
    now = now or datetime.now(timezone.utc)
    status = status.value if isinstance(status, TicketStatus) else status
    due = _parse(resolve_due)

    if status == TicketStatus.resolved.value:
        done = _parse(resolved_at) or now
        if due and done > due:
            return "missed"
        return "met"

    if not due:
        return "on_track"
    if now > due:
        return "breached"

    start = _parse(created_at)
    if start:
        total = (due - start).total_seconds()
        elapsed = (now - start).total_seconds()
        if total > 0 and elapsed / total >= _AT_RISK_FRACTION:
            return "at_risk"
    return "on_track"


# --- Impact × Urgency → Priority（标准 ITIL 3×3 → 4 级）---
_MATRIX: dict[tuple[Impact, Urgency], Priority] = {
    (Impact.high, Urgency.high): Priority.critical,
    (Impact.high, Urgency.medium): Priority.high,
    (Impact.medium, Urgency.high): Priority.high,
    (Impact.high, Urgency.low): Priority.medium,
    (Impact.medium, Urgency.medium): Priority.medium,
    (Impact.low, Urgency.high): Priority.medium,
    (Impact.medium, Urgency.low): Priority.low,
    (Impact.low, Urgency.medium): Priority.low,
    (Impact.low, Urgency.low): Priority.low,
}


def priority_from_matrix(impact: Impact, urgency: Urgency) -> Priority:
    """按 Impact×Urgency 矩阵推导优先级（用于在 UI 上和分类器优先级交叉验证）。"""
    return _MATRIX.get((impact, urgency), Priority.medium)
