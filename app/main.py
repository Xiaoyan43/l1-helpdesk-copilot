"""FastAPI 入口。阶段 2：分类 + KB 检索 + 带引用的回复。"""
from fastapi import FastAPI, File, UploadFile

from .classifier import classify
from .config import get_settings
from .data_io import load_tickets_csv, parse_tickets_bytes
from .kb import get_retriever
from .models import (
    Citation,
    Classification,
    Ticket,
    TriageItem,
    TriageResult,
)
from .responder import generate_reply

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
    """对粘贴的一条工单分类。"""
    return classify(ticket)


@app.get("/classify/sample", response_model=list[TriageItem])
def classify_sample() -> list[TriageItem]:
    """对内置样例 CSV 的每条工单分类。"""
    return [TriageItem(ticket=t, classification=classify(t)) for t in load_tickets_csv()]


@app.post("/ingest/csv", response_model=list[TriageItem])
async def ingest_csv(file: UploadFile = File(...)) -> list[TriageItem]:
    """上传一个工单 CSV（列 id,subject,body,requester），逐条分类。"""
    tickets = parse_tickets_bytes(await file.read())
    return [TriageItem(ticket=t, classification=classify(t)) for t in tickets]


@app.post("/respond", response_model=TriageResult)
def respond(ticket: Ticket, k: int = 2) -> TriageResult:
    """完整流水线：分类 → KB 检索 top-k → 生成带引用的 L1 回复。"""
    cl = classify(ticket)
    retriever = get_retriever()
    hits = retriever.search(f"{ticket.subject} {ticket.body}", k=k)
    articles = [a for a, _ in hits]
    reply = generate_reply(ticket, cl, articles)
    return TriageResult(
        ticket=ticket,
        classification=cl,
        citations=[Citation(id=a.id, title=a.title, score=round(s, 3))
                   for a, s in hits],
        reply=reply,
        retriever_mode=retriever.mode,
    )
