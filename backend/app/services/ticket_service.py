"""Ticket lifecycle: create (with instant rule-based triage + background AI triage), ownership
checks, status transitions, replies, internal notes, assignment, AI drafts.
"""

import logging
from datetime import datetime, timedelta
from uuid import uuid4

from app.ai import classifier, drafter, fallback
from app.core.config import get_settings
from app.core.exceptions import AIUnavailableError, AppError, ConflictError, NotFoundError
from app.repositories import ai_log_repository, book_repository, ticket_repository, user_repository
from app.schemas.auth import CurrentUser
from app.schemas.book import BookOut, BookRef
from app.schemas.common import (
    MIN_PAYOUT_THRESHOLD,
    PRIORITY_RANK,
    RESPONSE_SLA_HOURS,
    UNRESOLVED_STATUSES,
    ClassifiedBy,
    MessageKind,
    Priority,
    Role,
    TicketStatus,
)
from app.schemas.ticket import (
    AdminMessageCreate,
    AdminTicketDetail,
    AdminTicketSummary,
    AiTriageOut,
    AssigneeOut,
    AuthorProfileOut,
    AuthorTicketOut,
    DraftOut,
    MessageOut,
    TicketCreate,
    TicketStats,
    TicketUpdate,
)
from app.utils.dates import utcnow

logger = logging.getLogger(__name__)


# ============================================================ author side


async def create_ticket(user: CurrentUser, data: TicketCreate) -> AuthorTicketOut:
    """Creates the ticket immediately with rule-based triage. AI triage runs afterwards in the
    background (see run_ai_triage), so an AI outage can never block an author from raising a ticket."""
    book = None
    if data.book_id:
        book = await book_repository.find_for_author(data.book_id, user.author_id)
        if not book:
            raise NotFoundError("That book was not found in your account")

    rules = fallback.classify(data.subject, data.description, book["status"] if book else None)
    now = utcnow()
    doc = {
        "_id": await ticket_repository.next_ticket_number(),
        "author_id": user.author_id,
        "author_name": user.name,  # denormalised for queue display/search
        "book_id": data.book_id,
        "subject": data.subject,
        "description": data.description,
        "attachment_name": data.attachment_name,
        "status": TicketStatus.OPEN,
        "category": rules.category,
        "priority": rules.priority,
        "priority_rank": PRIORITY_RANK[rules.priority],
        "classified_by": ClassifiedBy.RULES,
        "rules": {"category": rules.category, "priority": rules.priority, "reason": rules.reason},
        "ai": None,
        "ai_draft": None,
        "assigned_to": None,
        "messages": [],
        "first_response_at": None,
        "resolved_at": None,
        "created_at": now,
        "updated_at": now,
        "last_activity_at": now,
    }
    await ticket_repository.insert(doc)
    return _author_view(doc, {book["_id"]: book} if book else {})


async def run_ai_triage(ticket_number: int) -> None:
    """Background task: refine category/priority with the LLM. Failures keep the rule-based result."""
    ticket = await ticket_repository.find(ticket_number)
    if not ticket:
        return
    book = await book_repository.find_by_id(ticket["book_id"]) if ticket.get("book_id") else None
    try:
        result = await classifier.classify(
            subject=ticket["subject"],
            description=ticket["description"],
            book_line=_triage_book_line(book) if book else None,
            ticket_number=ticket_number,
        )
    except AIUnavailableError as exc:
        logger.info("AI triage skipped for #%s, keeping rule-based result: %s", ticket_number, exc.message)
        return
    except Exception:
        logger.exception("Unexpected error during AI triage of #%s", ticket_number)
        return

    await ticket_repository.apply_ai_classification(
        ticket_number,
        ai={
            "category": result.category,
            "priority": result.priority,
            "reason": result.reason,
            "model": get_settings().groq_classify_model,
            "classified_at": utcnow(),
        },
        effective={
            "category": result.category,
            "priority": result.priority,
            "priority_rank": PRIORITY_RANK[result.priority],
        },
    )


def _triage_book_line(book: dict) -> str:
    """One compact line of facts that changes priority (e.g. a small pending amount under the payout
    threshold is routine, not urgent). Kept short because triage runs on every ticket."""
    pending = book.get("royalty_pending") or 0
    line = f'"{book["title"]}" ({book["status"]}); royalty pending ₹{pending:,}; last payout {book.get("last_royalty_payout_date") or "never"}'
    if 0 < pending < MIN_PAYOUT_THRESHOLD:
        line += f" (below the ₹{MIN_PAYOUT_THRESHOLD:,} payout threshold, so it rolls over by policy)"
    return line


async def list_author_tickets(user: CurrentUser) -> list[AuthorTicketOut]:
    tickets = await ticket_repository.list_for_author(user.author_id)
    books = await book_repository.find_by_ids([t["book_id"] for t in tickets if t.get("book_id")])
    return [_author_view(t, books) for t in tickets]


async def get_author_ticket(user: CurrentUser, number: int) -> AuthorTicketOut:
    """Opening a ticket marks its replies as read (only written when there's something unread, so
    the 5-second polling doesn't cause a database write every time)."""
    ticket = await _get_owned(user, number)
    if _has_unread_reply(ticket):
        ticket["author_last_read_at"] = utcnow()
        await ticket_repository.mark_read_by_author(number, ticket["author_last_read_at"])
    books = await book_repository.find_by_ids([ticket["book_id"]] if ticket.get("book_id") else [])
    return _author_view(ticket, books)


async def add_author_message(user: CurrentUser, number: int, body: str) -> AuthorTicketOut:
    ticket = await _get_owned(user, number)
    if ticket["status"] == TicketStatus.CLOSED:
        raise ConflictError("This ticket is closed. Please raise a new ticket if you still need help.")

    set_fields = {}
    if ticket["status"] == TicketStatus.RESOLVED:  # an author follow-up re-opens a resolved ticket
        set_fields = {"status": TicketStatus.OPEN, "resolved_at": None}
    updated = await ticket_repository.push_message(number, _new_message(user, body, MessageKind.REPLY), set_fields)
    books = await book_repository.find_by_ids([updated["book_id"]] if updated.get("book_id") else [])
    return _author_view(updated, books)


async def _get_owned(user: CurrentUser, number: int) -> dict:
    ticket = await ticket_repository.find_for_author(number, user.author_id)
    if not ticket:
        raise NotFoundError("Ticket not found")
    return ticket


# ============================================================ admin side


async def list_queue(admin: CurrentUser, filters: dict) -> list[AdminTicketSummary]:
    assigned = filters.pop("assigned", None)
    tickets = await ticket_repository.list_queue(
        **filters,
        assigned_to_id=admin.id if assigned == "me" else None,
        unassigned=assigned == "unassigned",
    )
    books = await book_repository.find_by_ids([t["book_id"] for t in tickets if t.get("book_id")])
    return [_summary_view(t, books) for t in tickets]


async def get_admin_ticket(number: int) -> AdminTicketDetail:
    ticket = await _get(number)
    author = await user_repository.find_by_author_id(ticket["author_id"])
    author_books = await book_repository.list_by_author(ticket["author_id"])
    books = {b["_id"]: b for b in author_books}
    summary = _summary_view(ticket, books)
    book = books.get(ticket.get("book_id"))
    return AdminTicketDetail(
        **summary.model_dump(),
        description=ticket["description"],
        attachment_name=ticket.get("attachment_name"),
        ai=AiTriageOut(**ticket["ai"]) if ticket.get("ai") else None,
        messages=[_message_view(m) for m in ticket["messages"]],
        author=AuthorProfileOut(
            author_id=ticket["author_id"],
            name=author["name"] if author else ticket["author_name"],
            email=author["email"] if author else "",
            phone=author.get("phone") if author else None,
            city=author.get("city") if author else None,
            joined_date=author.get("joined_date") if author else None,
        ),
        book_details=BookOut.from_doc(book) if book else None,
        author_books=[BookOut.from_doc(b) for b in author_books],
        first_response_at=ticket.get("first_response_at"),
        resolved_at=ticket.get("resolved_at"),
    )


async def update_ticket(number: int, data: TicketUpdate) -> AdminTicketDetail:
    ticket = await _get(number)
    changes: dict = {}
    fields = data.model_fields_set

    if "status" in fields and data.status:
        changes["status"] = data.status
        if data.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            changes["resolved_at"] = ticket.get("resolved_at") or utcnow()
        else:
            changes["resolved_at"] = None
    # A human override always wins: classified_by=ADMIN stops background AI from overwriting it.
    if "category" in fields and data.category:
        changes["category"] = data.category
        changes["classified_by"] = ClassifiedBy.ADMIN
    if "priority" in fields and data.priority:
        changes["priority"] = data.priority
        changes["priority_rank"] = PRIORITY_RANK[data.priority]
        changes["classified_by"] = ClassifiedBy.ADMIN
    if "assigned_to_id" in fields:
        changes["assigned_to"] = await _assignee(data.assigned_to_id) if data.assigned_to_id else None

    if changes:
        await ticket_repository.update(number, changes)
    return await get_admin_ticket(number)


async def add_admin_message(admin: CurrentUser, number: int, data: AdminMessageCreate) -> AdminTicketDetail:
    ticket = await _get(number)
    kind = MessageKind.NOTE if data.internal else MessageKind.REPLY
    set_fields: dict = {}

    if kind == MessageKind.REPLY:
        if not ticket.get("first_response_at"):
            set_fields["first_response_at"] = utcnow()
        # Sensible defaults: replying moves an open ticket into progress and claims it if unassigned.
        new_status = data.set_status or (
            TicketStatus.IN_PROGRESS if ticket["status"] == TicketStatus.OPEN else ticket["status"]
        )
        set_fields["status"] = new_status
        if new_status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            set_fields["resolved_at"] = utcnow()
        if not ticket.get("assigned_to"):
            set_fields["assigned_to"] = {"id": admin.id, "name": admin.name}
    elif data.set_status:
        set_fields["status"] = data.set_status

    await ticket_repository.push_message(
        number, _new_message(admin, data.body, kind, ai_assisted=data.ai_assisted and kind == MessageKind.REPLY), set_fields
    )
    return await get_admin_ticket(number)


async def get_draft(number: int, regenerate: bool) -> DraftOut:
    """Returns the cached AI draft when it's still valid; otherwise generates a new one.

    The cache is valid while the thread hasn't changed (same message count) and the category is the
    same (the category decides which KB sections are in the prompt). This means opening a ticket
    repeatedly, or several admins viewing it, costs tokens only once.
    """
    ticket = await _get(number)
    cached = ticket.get("ai_draft")
    if (
        cached
        and not regenerate
        and cached.get("message_count") == len(ticket["messages"])
        and cached.get("category") == ticket["category"]
    ):
        return DraftOut(text=cached["text"], model=cached["model"], generated_at=cached["generated_at"], cached=True)

    if not regenerate and not _awaiting_reply(ticket):
        raise ConflictError(
            "The latest message is already a BookLeaf reply, so there's nothing to draft. Use regenerate to draft a follow-up."
        )

    author = await user_repository.find_by_author_id(ticket["author_id"]) or {"name": ticket["author_name"]}
    author_books = await book_repository.list_by_author(ticket["author_id"])
    book = next((b for b in author_books if b["_id"] == ticket.get("book_id")), None)

    text = await drafter.generate_draft(  # raises AIUnavailableError -> 503, admin writes manually
        ticket=ticket, author=author, book=book, author_books=author_books, today=utcnow().date()
    )
    draft = {
        "text": text,
        "model": get_settings().groq_draft_model,
        "generated_at": utcnow(),
        "message_count": len(ticket["messages"]),
        "category": ticket["category"],
    }
    await ticket_repository.save_draft(number, draft)
    return DraftOut(text=text, model=draft["model"], generated_at=draft["generated_at"], cached=False)


async def get_stats() -> TicketStats:
    raw = await ticket_repository.stats()
    now = utcnow()
    overrides = (raw["overrides"] or [{}])[0]
    ai_classified = overrides.get("ai_classified", 0)
    return TicketStats(
        by_status={s: 0 for s in TicketStatus} | {r["_id"]: r["n"] for r in raw["by_status"]},
        unresolved_by_priority={p: 0 for p in Priority} | {r["_id"]: r["n"] for r in raw["unresolved_by_priority"]},
        unassigned_unresolved=(raw["unassigned_unresolved"] or [{"n": 0}])[0]["n"],
        sla_breached=sum(1 for t in raw["unanswered"] if _is_overdue(t["priority"], t["created_at"], now)),
        ai={
            "last_7_days": await ai_log_repository.usage_summary(days=7),
            "classified_by_ai": ai_classified,
            "category_override_rate": round(overrides.get("category_overridden", 0) / ai_classified, 2) if ai_classified else None,
            "priority_override_rate": round(overrides.get("priority_overridden", 0) / ai_classified, 2) if ai_classified else None,
        },
    )


async def list_admins() -> list[AssigneeOut]:
    return [AssigneeOut(id=a["_id"], name=a["name"]) for a in await user_repository.list_admins()]


async def _get(number: int) -> dict:
    ticket = await ticket_repository.find(number)
    if not ticket:
        raise NotFoundError("Ticket not found")
    return ticket


async def _assignee(user_id: str) -> dict:
    user = await user_repository.find_by_id(user_id)
    if not user or user["role"] != Role.ADMIN:
        raise AppError("Tickets can only be assigned to an admin user", {"assigned_to_id": "Unknown admin"})
    return {"id": user["_id"], "name": user["name"]}


# ============================================================ mapping helpers


def _new_message(sender: CurrentUser, body: str, kind: MessageKind, *, ai_assisted: bool = False) -> dict:
    return {
        "id": uuid4().hex,
        "kind": kind,
        "sender_id": sender.id,
        "sender_role": sender.role,
        "sender_name": sender.name,
        "body": body,
        "ai_assisted": ai_assisted,
        "created_at": utcnow(),
    }


def _message_view(m: dict) -> MessageOut:
    return MessageOut(**{k: m.get(k) for k in MessageOut.model_fields if k in m})


def _book_ref(book_id: str | None, books: dict[str, dict]) -> BookRef | None:
    book = books.get(book_id) if book_id else None
    return BookRef(id=book["_id"], title=book["title"], isbn=book["isbn"], status=book["status"]) if book else None


def _author_view(t: dict, books: dict[str, dict]) -> AuthorTicketOut:
    return AuthorTicketOut(
        ticket_number=t["_id"],
        subject=t["subject"],
        description=t["description"],
        attachment_name=t.get("attachment_name"),
        status=t["status"],
        category=t["category"],
        book=_book_ref(t.get("book_id"), books),
        # Internal notes are removed here, on the server; they never reach an author's browser.
        messages=[_message_view(m) for m in ticket_repository.visible_to_author(t.get("messages", []))],
        unread_reply=_has_unread_reply(t),
        created_at=t["created_at"],
        updated_at=t["updated_at"],
    )


def _has_unread_reply(t: dict) -> bool:
    last_read = t.get("author_last_read_at")
    return any(
        m["kind"] == MessageKind.REPLY
        and m["sender_role"] == Role.ADMIN
        and (last_read is None or m["created_at"] > last_read)
        for m in t.get("messages", [])
    )


def _awaiting_reply(t: dict) -> bool:
    replies = ticket_repository.visible_to_author(t.get("messages", []))
    return t["status"] in UNRESOLVED_STATUSES and (not replies or replies[-1]["sender_role"] == Role.AUTHOR)


def _is_overdue(priority: str, created_at: datetime, now: datetime) -> bool:
    return now - created_at > timedelta(hours=RESPONSE_SLA_HOURS[Priority(priority)])


def _summary_view(t: dict, books: dict[str, dict]) -> AdminTicketSummary:
    unresolved = t["status"] in UNRESOLVED_STATUSES
    return AdminTicketSummary(
        ticket_number=t["_id"],
        subject=t["subject"],
        author_id=t["author_id"],
        author_name=t["author_name"],
        book=_book_ref(t.get("book_id"), books),
        status=t["status"],
        category=t["category"],
        priority=t["priority"],
        classified_by=t["classified_by"],
        assigned_to=AssigneeOut(**t["assigned_to"]) if t.get("assigned_to") else None,
        message_count=len(t.get("messages", [])),
        awaiting_reply=_awaiting_reply(t),
        sla_breached=unresolved and not t.get("first_response_at") and _is_overdue(t["priority"], t["created_at"], utcnow()),
        created_at=t["created_at"],
        updated_at=t["updated_at"],
    )
