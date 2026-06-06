"""生成带 KB 引用的 L1 回复（RAG 的 G）。

- 有 key 且 USE_MOCK_LLM=false → Claude 基于检索到的 KB 写回复，并引用 [KBxxx]。
- 否则 → 本地模板回复（同样引用 top 文章），保证离线可 demo。
严格约束：只依据提供的 KB 内容作答，不要编造步骤。
"""
import re
from collections.abc import Iterator

from .classifier import _get_client
from .config import get_settings
from .kb import Article
from .models import Classification, Reply, Ticket

_SYSTEM = (
    "You are an L1 IT help desk agent writing a first reply to the end user. "
    "Use ONLY the provided knowledge base context; do not invent steps or policies. "
    "Write a concise, friendly, professional reply (no more than ~150 words): greet, "
    "acknowledge the issue, give the first 2-4 concrete steps from the KB, and cite the "
    "article inline like [KB001]. If identity verification or approval is required, say so. "
    "End by inviting the user to reply if it isn't resolved. Sign as 'IT Service Desk'."
)


def _context(articles: list[Article]) -> str:
    return "\n\n".join(f"[{a.id}] {a.title}\n{a.text}" for a in articles)


def _extract_steps(article: Article, limit: int = 3) -> list[str]:
    steps = [
        re.sub(r"^\s*\d+\.\s*", "", ln).strip()
        for ln in article.text.splitlines()
        if re.match(r"\s*\d+\.\s+", ln)
    ]
    return steps[:limit]


def _mock_reply(ticket: Ticket, cl: Classification, articles: list[Article]) -> Reply:
    name = (ticket.requester or "").split("@")[0] or "there"
    top = articles[0] if articles else None
    lines = [f"Hi {name},", ""]
    lines.append(
        f"Thanks for reaching out — this looks like a {cl.category.value} "
        f"{cl.ticket_type.value} (priority: {cl.priority.value})."
    )
    if top:
        lines.append("")
        lines.append(f"Per our guide [{top.id}] {top.title}, please try:")
        for i, step in enumerate(_extract_steps(top), 1):
            lines.append(f"  {i}. {step}")
    lines += ["", "If that doesn't resolve it, reply here and we'll take the next step.",
              "", "Best regards,", "IT Service Desk"]
    return Reply(
        reply_text="\n".join(lines),
        cited_kb=[a.id for a in articles],
        source="mock",
    )


def _user_message(ticket: Ticket, cl: Classification, articles: list[Article]) -> str:
    return (
        f"Ticket subject: {ticket.subject}\n"
        f"Ticket body: {ticket.body}\n"
        f"Requester: {ticket.requester or 'unknown'}\n"
        f"Triage: {cl.category.value} / {cl.priority.value} / {cl.ticket_type.value}\n\n"
        f"Knowledge base context:\n{_context(articles)}"
    )


def reply_source() -> str:
    s = get_settings()
    return "mock" if s.use_mock_llm or not s.anthropic_api_key else "claude"


def generate_reply(
    ticket: Ticket, cl: Classification, articles: list[Article]
) -> Reply:
    s = get_settings()
    if s.use_mock_llm or not s.anthropic_api_key:
        return _mock_reply(ticket, cl, articles)

    resp = _get_client().messages.create(
        model=s.respond_model,
        max_tokens=600,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _user_message(ticket, cl, articles)}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return Reply(reply_text=text, cited_kb=[a.id for a in articles], source="claude")


def stream_reply(
    ticket: Ticket, cl: Classification, articles: list[Article]
) -> Iterator[str]:
    """Yield reply text chunks (Claude streaming, or word-chunked mock)."""
    s = get_settings()
    if s.use_mock_llm or not s.anthropic_api_key:
        text = _mock_reply(ticket, cl, articles).reply_text
        for i, word in enumerate(text.split()):
            yield word if i == 0 else " " + word
        return

    with _get_client().messages.stream(
        model=s.respond_model,
        max_tokens=600,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _user_message(ticket, cl, articles)}],
    ) as stream:
        yield from stream.text_stream
