"""工单 CSV 读写。

CSV 列：id, subject, body, requester, gold_category, gold_priority,
gold_ticket_type, gold_kb_hit
gold_* 是人工标注，分类时忽略，仅评测（阶段3）用。
"""
import csv
import io
from pathlib import Path

from .models import Ticket

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = PROJECT_ROOT / "data" / "sample_tickets.csv"


def _row_to_ticket(r: dict) -> Ticket:
    return Ticket(
        id=(r.get("id") or "").strip() or None,
        subject=(r.get("subject") or "").strip(),
        body=(r.get("body") or "").strip(),
        requester=(r.get("requester") or "").strip() or None,
    )


def load_tickets_csv(path: str | Path = SAMPLE_CSV) -> list[Ticket]:
    with open(path, newline="", encoding="utf-8") as f:
        return [_row_to_ticket(r) for r in csv.DictReader(f)]


def parse_tickets_bytes(raw: bytes) -> list[Ticket]:
    """从上传的 CSV 字节流解析工单。"""
    text = raw.decode("utf-8-sig")
    return [_row_to_ticket(r) for r in csv.DictReader(io.StringIO(text))]


def load_labeled_rows(path: str | Path = SAMPLE_CSV) -> list[dict]:
    """返回含 gold_* 标注的原始行（评测用）。"""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
