"""Author ticket routes: list / create / view own tickets, and post follow-up messages."""

from fastapi import APIRouter, BackgroundTasks, Path, status

from app.api.deps import AuthorUser
from app.schemas.ticket import AuthorMessageCreate, AuthorTicketOut, TicketCreate
from app.services import ticket_service

router = APIRouter()

TicketNumber = Path(ge=1, description="Ticket number, e.g. 1001")


@router.get("", response_model=list[AuthorTicketOut], summary="List my tickets (most recently updated first)")
async def list_my_tickets(user: AuthorUser) -> list[AuthorTicketOut]:
    return await ticket_service.list_author_tickets(user)


@router.post(
    "",
    response_model=AuthorTicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a support ticket",
    description="Created instantly with rule-based triage; AI classification refines it in the background.",
)
async def create_ticket(body: TicketCreate, user: AuthorUser, background: BackgroundTasks) -> AuthorTicketOut:
    ticket = await ticket_service.create_ticket(user, body)
    background.add_task(ticket_service.run_ai_triage, ticket.ticket_number)
    return ticket


@router.get("/{ticket_number}", response_model=AuthorTicketOut, summary="Get one of my tickets")
async def get_my_ticket(user: AuthorUser, ticket_number: int = TicketNumber) -> AuthorTicketOut:
    return await ticket_service.get_author_ticket(user, ticket_number)


@router.post(
    "/{ticket_number}/messages",
    response_model=AuthorTicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a follow-up message to my ticket",
)
async def add_message(body: AuthorMessageCreate, user: AuthorUser, ticket_number: int = TicketNumber) -> AuthorTicketOut:
    return await ticket_service.add_author_message(user, ticket_number, body.body)
