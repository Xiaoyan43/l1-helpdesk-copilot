"""FastAPI 入口。分类 + RAG 回复 + Graph 动作 + 工单生命周期 + 审计 + 单页 UI。"""
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from . import store
from .audit import init_audit_db, log_event, read_events
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
    CommentRequest,
    CreateTicketRequest,
    CreateUserRequest,
    EscalateRequest,
    Feedback,
    ResetPasswordRequest,
    ResolveRequest,
    StatusChangeRequest,
    StoredTicket,
    Ticket,
    TicketStatus,
    TriageItem,
    TriageResult,
)
from .responder import generate_reply, reply_source, stream_reply

app = FastAPI(
    title="L1 HelpDesk Copilot (lab / portfolio)",
    description=(
        "Personal portfolio project — runs only on sample tickets and a lab tenant, not production."
    ),
    version="0.2.0",
)

# 启动即建表并铺底（首启把 50 条样本工单填进队列）。规则基线 seeding，不烧 API。
store.init_db()
init_audit_db()
store.seed_if_empty()


_INDEX = Path(__file__).resolve().parent / "static" / "index.html"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _require(ticket_id: str) -> StoredTicket:
    t = store.get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")
    return t


def _retrieve(ticket: Ticket, k: int = 2):
    """Retrieve top-k KB hits for a ticket."""
    retriever = get_retriever()
    hits = retriever.search(f"{ticket.subject} {ticket.body}", k=k)
    citations = [Citation(id=a.id, title=a.title, score=round(s, 3)) for a, s in hits]
    return citations, [a for a, _ in hits], retriever.mode


def _draft(ticket: Ticket, cl: Classification, k: int = 2):
    """检索 top-k KB 并起草回复（/respond 与 /tickets/{id}/respond 共用）。"""
    citations, articles, mode = _retrieve(ticket, k)
    reply = generate_reply(ticket, cl, articles)
    return citations, reply, mode


def _ticket_classification(t: StoredTicket) -> Classification:
    return Classification(
        category=t.category, priority=t.priority, ticket_type=t.ticket_type,
        impact=t.impact, urgency=t.urgency, kb_hit=t.kb_hit, confidence=t.confidence,
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Minimal single-page UI."""
    return _INDEX.read_text(encoding="utf-8")


@app.get("/tickets", response_model=list[StoredTicket])
def tickets(status: str | None = None) -> list[StoredTicket]:
    """The ticket queue (optionally filtered by ?status=)."""
    return store.list_tickets(status)


@app.get("/tickets/{ticket_id}", response_model=StoredTicket)
def get_ticket(ticket_id: str) -> StoredTicket:
    """One ticket with its full timeline."""
    return _require(ticket_id)


@app.post("/tickets", response_model=StoredTicket)
def create_ticket(req: CreateTicketRequest) -> StoredTicket:
    """Intake a new ticket; auto-triage it (classify + impact/urgency) and store as 'new'."""
    ticket = Ticket(subject=req.subject, body=req.body, requester=req.requester)
    cl = classify(ticket)
    t = store.create_ticket(ticket, cl, channel=req.channel, status=TicketStatus.new)
    store.add_event(t.id, "created", f"Ticket created via {req.channel.value}", actor="requester")
    store.add_event(
        t.id, "triaged",
        f"Auto-triaged: {cl.category.value} / {cl.ticket_type.value} / priority "
        f"{cl.priority.value} (impact {cl.impact.value}, urgency {cl.urgency.value})",
        actor="system", detail={"reasoning": cl.reasoning, "source": cl.source},
    )
    log_event("classification", ticket=ticket.model_dump(),
              classification=cl.model_dump(), ticket_id=t.id)
    return _require(t.id)


@app.post("/tickets/{ticket_id}/triage", response_model=StoredTicket)
def triage_ticket(ticket_id: str) -> StoredTicket:
    """Re-run AI triage on a stored ticket (updates classification + SLA clock)."""
    t = _require(ticket_id)
    ticket = Ticket(id=t.id, subject=t.subject, body=t.body, requester=t.requester)
    cl = classify(ticket)
    resp_due, res_due = store.sla.due_dates(t.created_at, cl.priority)
    store.update_ticket(
        ticket_id, category=cl.category, ticket_type=cl.ticket_type,
        impact=cl.impact, urgency=cl.urgency, priority=cl.priority,
        kb_hit=cl.kb_hit, confidence=cl.confidence,
        sla_response_due=resp_due, sla_resolve_due=res_due,
    )
    store.add_event(
        ticket_id, "triaged",
        f"AI re-triage ({cl.source}): {cl.category.value} / {cl.ticket_type.value} / "
        f"priority {cl.priority.value} (impact {cl.impact.value}, urgency {cl.urgency.value})",
        actor="L1 Agent", detail={"reasoning": cl.reasoning},
    )
    log_event("classification", ticket=ticket.model_dump(),
              classification=cl.model_dump(), ticket_id=ticket_id)
    return _require(ticket_id)


@app.post("/tickets/{ticket_id}/respond", response_model=TriageResult)
def respond_ticket(ticket_id: str, k: int = 2) -> TriageResult:
    """Draft a cited L1 reply for a stored ticket (uses its stored triage)."""
    t = _require(ticket_id)
    ticket = Ticket(id=t.id, subject=t.subject, body=t.body, requester=t.requester)
    cl = _ticket_classification(t)
    citations, reply, mode = _draft(ticket, cl, k)
    store.add_event(
        ticket_id, "reply_drafted",
        f"Drafted L1 reply ({reply.source}); cited {', '.join(reply.cited_kb) or 'none'}",
        actor="L1 Agent",
    )
    return TriageResult(ticket=ticket, classification=cl, citations=citations,
                        reply=reply, retriever_mode=mode)


@app.post("/tickets/{ticket_id}/respond/stream")
def respond_ticket_stream(ticket_id: str, k: int = 2) -> StreamingResponse:
    """Stream a cited L1 reply as Server-Sent Events (token chunks + final metadata)."""
    t = _require(ticket_id)
    ticket = Ticket(id=t.id, subject=t.subject, body=t.body, requester=t.requester)
    cl = _ticket_classification(t)
    citations, articles, mode = _retrieve(ticket, k)
    source = reply_source()
    cited_kb = [a.id for a in articles]

    def gen():
        parts: list[str] = []
        yield _sse({
            "type": "meta",
            "citations": [c.model_dump() for c in citations],
            "retriever_mode": mode,
            "source": source,
        })
        for chunk in stream_reply(ticket, cl, articles):
            parts.append(chunk)
            yield _sse({"type": "token", "text": chunk})
        full = "".join(parts)
        store.add_event(
            ticket_id, "reply_drafted",
            f"Drafted L1 reply ({source}, streamed); cited {', '.join(cited_kb) or 'none'}",
            actor="L1 Agent",
        )
        yield _sse({
            "type": "done",
            "reply_text": full,
            "cited_kb": cited_kb,
            "source": source,
        })

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/tickets/{ticket_id}/status", response_model=StoredTicket)
def change_status(ticket_id: str, req: StatusChangeRequest) -> StoredTicket:
    """Move a ticket through its lifecycle (start / wait on user / etc.)."""
    t = _require(ticket_id)
    fields: dict = {"status": req.status}
    if req.status == TicketStatus.in_progress and not t.assignee:
        fields["assignee"] = "L1 Agent"
    if req.status == TicketStatus.resolved and not t.resolved_at:
        fields["resolved_at"] = _now()
    store.update_ticket(ticket_id, **fields)
    summary = f"Status → {req.status.value}" + (f": {req.note}" if req.note else "")
    store.add_event(ticket_id, "status_change", summary, actor="L1 Agent")
    log_event("ticket_status", ticket_id=ticket_id, status=req.status.value, note=req.note)
    return _require(ticket_id)


@app.post("/tickets/{ticket_id}/escalate", response_model=StoredTicket)
def escalate_ticket(ticket_id: str, req: EscalateRequest) -> StoredTicket:
    """Escalate to an L2 / specialist team with a reason."""
    _require(ticket_id)
    store.update_ticket(ticket_id, status=TicketStatus.escalated,
                        escalation_team=req.team, escalation_reason=req.reason)
    store.add_event(ticket_id, "escalated",
                    f"Escalated to {req.team.value}: {req.reason}", actor="L1 Agent")
    log_event("ticket_escalated", ticket_id=ticket_id,
              team=req.team.value, reason=req.reason)
    return _require(ticket_id)


@app.post("/tickets/{ticket_id}/resolve", response_model=StoredTicket)
def resolve_ticket(ticket_id: str, req: ResolveRequest) -> StoredTicket:
    """Resolve a ticket with a closure/resolution code."""
    _require(ticket_id)
    store.update_ticket(ticket_id, status=TicketStatus.resolved,
                        resolution_code=req.resolution_code,
                        resolution_notes=req.notes, resolved_at=_now())
    summary = f"Resolved ({req.resolution_code.value})" + (f": {req.notes}" if req.notes else "")
    store.add_event(ticket_id, "resolved", summary, actor="L1 Agent")
    log_event("ticket_resolved", ticket_id=ticket_id,
              resolution_code=req.resolution_code.value)
    return _require(ticket_id)


@app.post("/tickets/{ticket_id}/comment", response_model=StoredTicket)
def comment_ticket(ticket_id: str, req: CommentRequest) -> StoredTicket:
    """Add a free-text worklog note to the timeline."""
    _require(ticket_id)
    store.add_event(ticket_id, "comment", req.note, actor=req.actor)
    store.update_ticket(ticket_id)   # bump updated_at
    return _require(ticket_id)


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
    citations, reply, mode = _draft(ticket, cl, k)
    log_event(
        "classification",
        ticket=ticket.model_dump(),
        classification=cl.model_dump(),
        citations=[c.model_dump() for c in citations],
        reply_source=reply.source,
    )
    return TriageResult(ticket=ticket, classification=cl, citations=citations,
                        reply=reply, retriever_mode=mode)


# --- Microsoft Graph 账号动作（默认 dry-run；详见 docs/m365-setup.md） ---
def _record_action_on_ticket(ticket_id: str | None, res: ActionResult) -> None:
    """若动作关联了某工单，把它写进该工单 timeline（密码已在 res.request 里脱敏）。"""
    if not ticket_id or not store.get_ticket(ticket_id):
        return
    tag = "dry-run" if res.dry_run else "LIVE"
    state = "ok" if res.success else "failed"
    store.add_event(
        ticket_id, "graph_action",
        f"{res.action} ({tag}) — {res.summary} [{state}]", actor="L1 Agent",
        detail={"request": res.request, "graph_status": res.graph_status},
    )


@app.post("/actions/create-user", response_model=ActionResult)
def act_create_user(req: CreateUserRequest) -> ActionResult:
    res = create_user(req)
    _record_action_on_ticket(req.ticket_id, res)
    return res


@app.post("/actions/reset-password", response_model=ActionResult)
def act_reset_password(req: ResetPasswordRequest) -> ActionResult:
    res = reset_password(req)
    _record_action_on_ticket(req.ticket_id, res)
    return res


@app.post("/actions/add-to-group", response_model=ActionResult)
def act_add_to_group(req: AddToGroupRequest) -> ActionResult:
    res = add_to_group(req)
    _record_action_on_ticket(req.ticket_id, res)
    return res


@app.post("/actions/assign-license", response_model=ActionResult)
def act_assign_license(req: AssignLicenseRequest) -> ActionResult:
    res = assign_license(req)
    _record_action_on_ticket(req.ticket_id, res)
    return res


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
    """Log operator feedback on a reply (resolved/escalate) to the audit log + timeline."""
    log_event("feedback", **fb.model_dump())
    if fb.ticket_id and store.get_ticket(fb.ticket_id):
        verdict = "agrees the draft resolves it" if fb.status == "resolved" \
            else "flags the draft for escalation"
        store.add_event(fb.ticket_id, "feedback", f"L1 review: {verdict}", actor="L1 Agent")
    return {"ok": True}


# --- 审计日志 ---
@app.get("/audit")
def audit(limit: int = 100) -> list[dict]:
    return read_events(limit)
