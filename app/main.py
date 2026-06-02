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
    title="L1 HelpDesk Copilot (lab / portfolio)",
    description="Personal portfolio project — runs only on sample tickets and a lab tenant, not production.",
    version="0.1.0",
)


_INDEX = Path(__file__).resolve().parent / "static" / "index.html"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Minimal single-page UI."""
    return _INDEX.read_text(encoding="utf-8")


@app.get("/tickets", response_model=list[Ticket])
def tickets() -> list[Ticket]:
    """Bundled sample tickets (for the UI dropdown)."""
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
    """Classify a single pasted ticket."""
    c = classify(ticket)
    log_event("classification", ticket=ticket.model_dump(), classification=c.model_dump())
    return c


@app.get("/classify/sample", response_model=list[TriageItem])
def classify_sample() -> list[TriageItem]:
    """Classify every ticket in the bundled sample CSV."""
    return [TriageItem(ticket=t, classification=classify(t)) for t in load_tickets_csv()]


@app.post("/ingest/csv", response_model=list[TriageItem])
async def ingest_csv(file: UploadFile = File(...)) -> list[TriageItem]:
    """Upload a ticket CSV (columns id,subject,body,requester) and classify each row."""
    tickets = parse_tickets_bytes(await file.read())
    return [TriageItem(ticket=t, classification=classify(t)) for t in tickets]


@app.post("/respond", response_model=TriageResult)
def respond(ticket: Ticket, k: int = 2) -> TriageResult:
    """Full pipeline: classify -> retrieve top-k KB -> draft a cited L1 reply."""
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
    """Log operator feedback on a reply (resolved/escalate) to the audit log."""
    log_event("feedback", **fb.model_dump())
    return {"ok": True}


# --- 审计日志 ---
@app.get("/audit")
def audit(limit: int = 100) -> list[dict]:
    return read_events(limit)
