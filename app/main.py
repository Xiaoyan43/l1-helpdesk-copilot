"""FastAPI 入口。阶段 5：分类 + RAG 回复 + Graph 动作 + 审计 + 单页 UI。"""
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

from .audit import log_event, read_events
from .classifier import classify
from .config import get_settings
from .data_io import load_tickets_csv, parse_tickets_bytes
from .graph_actions import (
    _creds_ready,
    add_to_group,
    assign_license,
    create_user,
    list_groups,
    list_skus,
    list_users,
    reset_password,
)
from .kb import get_retriever
from .models import (
    ActionResult,
    AddToGroupRequest,
    AssignLicenseRequest,
    Citation,
    Classification,
    CreateUserRequest,
    Feedback,
    ResetPasswordRequest,
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


_INDEX = Path(__file__).resolve().parent / "static" / "index.html"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """极简单页 UI。"""
    return _INDEX.read_text(encoding="utf-8")


@app.get("/tickets", response_model=list[Ticket])
def tickets() -> list[Ticket]:
    """内置样例工单（供 UI 下拉载入）。"""
    return load_tickets_csv()


@app.get("/healthz")
def healthz() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "use_mock_llm": s.use_mock_llm,
        "graph_dry_run": s.graph_dry_run,
        "has_anthropic_key": bool(s.anthropic_api_key),
        "graph_creds_ready": _creds_ready(),
        "action_confidence_threshold": s.action_confidence_threshold,
    }


@app.post("/classify", response_model=Classification)
def classify_endpoint(ticket: Ticket) -> Classification:
    """对粘贴的一条工单分类。"""
    c = classify(ticket)
    log_event("classification", ticket=ticket.model_dump(), classification=c.model_dump())
    return c


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
    result = TriageResult(
        ticket=ticket,
        classification=cl,
        citations=[Citation(id=a.id, title=a.title, score=round(s, 3))
                   for a, s in hits],
        reply=reply,
        retriever_mode=retriever.mode,
    )
    log_event(
        "classification",
        ticket=ticket.model_dump(),
        classification=cl.model_dump(),
        citations=[c.model_dump() for c in result.citations],
        reply_source=reply.source,
    )
    return result


# --- Microsoft Graph 账号动作（默认 dry-run；详见 docs/m365-setup.md） ---
@app.post("/actions/create-user", response_model=ActionResult)
def act_create_user(req: CreateUserRequest) -> ActionResult:
    return create_user(req)


@app.post("/actions/reset-password", response_model=ActionResult)
def act_reset_password(req: ResetPasswordRequest) -> ActionResult:
    return reset_password(req)


@app.post("/actions/add-to-group", response_model=ActionResult)
def act_add_to_group(req: AddToGroupRequest) -> ActionResult:
    return add_to_group(req)


@app.post("/actions/assign-license", response_model=ActionResult)
def act_assign_license(req: AssignLicenseRequest) -> ActionResult:
    return assign_license(req)


# --- 只读：发现租户里的 id（需真实凭据） ---
@app.get("/graph/users")
def graph_users(top: int = 15) -> dict:
    return list_users(top)


@app.get("/graph/groups")
def graph_groups(top: int = 30) -> dict:
    return list_groups(top)


@app.get("/graph/skus")
def graph_skus() -> dict:
    return list_skus()


# --- 人在环反馈 ---
@app.post("/feedback")
def feedback(fb: Feedback) -> dict:
    """记录操作员对回复的反馈（已解决/需升级）到审计日志。"""
    log_event("feedback", **fb.model_dump())
    return {"ok": True}


# --- 审计日志 ---
@app.get("/audit")
def audit(limit: int = 100) -> list[dict]:
    return read_events(limit)
