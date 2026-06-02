"""极简审计日志：每条事件追加一行 JSON 到 audit_log.jsonl。

记录两类事件：'classification'（每次分类）与 'graph_action'（每次账号动作）。
注意：明文密码绝不写入审计（见 graph_actions._run）。
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .config import get_settings
from .data_io import PROJECT_ROOT

_lock = threading.Lock()


def _path() -> Path:
    p = Path(get_settings().audit_log_path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def log_event(kind: str, **data) -> dict:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        **data,
    }
    with _lock, open(_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_events(limit: int = 100) -> list[dict]:
    p = _path()
    if not p.exists():
        return []
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines[-limit:]][::-1]   # 最新在前
