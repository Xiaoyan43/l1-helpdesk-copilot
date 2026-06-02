"""FastAPI 入口。阶段 0：健康检查 + 规则基线分类，已可跑。"""
from fastapi import FastAPI

from .classifier import classify
from .config import get_settings
from .models import Classification, Ticket

app = FastAPI(
    title="L1 HelpDesk Copilot (lab / 作品)",
    description="个人作品，仅对样例工单 + lab 租户运行，非生产系统。",
    version="0.1.0",
)


@app.get("/healthz")
def healthz() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "use_mock_llm": s.use_mock_llm,
        "graph_dry_run": s.graph_dry_run,
        "has_anthropic_key": bool(s.anthropic_api_key),
    }


@app.post("/classify", response_model=Classification)
def classify_endpoint(ticket: Ticket) -> Classification:
    """对一条工单分类（阶段 0 走规则基线）。"""
    return classify(ticket)
