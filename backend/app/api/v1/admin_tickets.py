"""Admin routes: ticket queue with filters, ticket detail, update status/category/priority/assignee,
replies and internal notes, AI draft generation, dashboard stats, admin list.
"""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminUser
from app.schemas.common import Category, Priority, TicketStatus
from app.schemas.ticket import (
    AdminMessageCreate,
    AdminTicketDetail,
    AdminTicketSummary,
    AssigneeOut,
    DraftOut,
    DraftRequest,
    TicketStats,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter()

TicketNumber = Path(ge=1, description="Ticket number, e.g. 1001")


@router.get("/tickets", response_model=list[AdminTicketSummary], summary="Ticket queue (urgent and oldest first)")
async def list_tickets(
    admin: AdminUser,
    status_: Annotated[
        TicketStatus | Literal["UNRESOLVED"] | None,
        Query(alias="status", description="A status, or UNRESOLVED for Open + In Progress"),
    ] = None,
    category: Category | None = None,
    priority: Priority | None = None,
    assigned: Annotated[Literal["me", "unassigned"] | None, Query(description="Only mine, or only unassigned")] = None,
    created_from: Annotated[datetime | None, Query(alias="from", description="Created on/after (ISO date)")] = None,
    created_to: Annotated[datetime | None, Query(alias="to", description="Created on/before (ISO date)")] = None,
    q: Annotated[str | None, Query(max_length=100, description="Search subject, author name or ticket number")] = None,
) -> list[AdminTicketSummary]:
    return await ticket_service.list_queue(
        admin,
        {
            "status": status_,
            "category": category,
            "priority": priority,
            "assigned": assigned,
            "created_from": created_from,
            "created_to": created_to,
            "search": q.strip() if q else None,
        },
    )


@router.get("/tickets/{ticket_number}", response_model=AdminTicketDetail, summary="Full ticket incl. internal notes and author context")
async def get_ticket(_: AdminUser, ticket_number: int = TicketNumber) -> AdminTicketDetail:
    return await ticket_service.get_admin_ticket(ticket_number)


@router.patch(
    "/tickets/{ticket_number}",
    response_model=AdminTicketDetail,
    summary="Update status, override category/priority, assign/unassign",
)
async def update_ticket(body: TicketUpdate, _: AdminUser, ticket_number: int = TicketNumber) -> AdminTicketDetail:
    return await ticket_service.update_ticket(ticket_number, body)


@router.post(
    "/tickets/{ticket_number}/messages",
    response_model=AdminTicketDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Send a reply to the author, or add an internal note (internal=true)",
)
async def add_message(body: AdminMessageCreate, admin: AdminUser, ticket_number: int = TicketNumber) -> AdminTicketDetail:
    return await ticket_service.add_admin_message(admin, ticket_number, body)


@router.post(
    "/tickets/{ticket_number}/draft",
    response_model=DraftOut,
    summary="Get the AI-drafted reply (cached unless the thread changed or regenerate=true)",
    responses={
        409: {"description": "Nothing to reply to (last message is already from BookLeaf)"},
        503: {"description": "AI unavailable; the admin writes the reply manually"},
    },
)
async def draft_reply(_: AdminUser, body: DraftRequest | None = None, ticket_number: int = TicketNumber) -> DraftOut:
    return await ticket_service.get_draft(ticket_number, regenerate=bool(body and body.regenerate))


@router.get("/stats", response_model=TicketStats, summary="Queue health and AI usage/accuracy metrics")
async def stats(_: AdminUser) -> TicketStats:
    return await ticket_service.get_stats()


@router.get("/users", response_model=list[AssigneeOut], summary="Admin users (for assignment)")
async def list_admins(_: AdminUser) -> list[AssigneeOut]:
    return await ticket_service.list_admins()
