"""Ticket request/response models for both the author view (no internal notes) and the admin view."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.book import BookOut, BookRef
from app.schemas.common import Category, ClassifiedBy, MessageKind, Priority, Role, TicketStatus

_strip = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ---------- Requests ----------


class TicketCreate(BaseModel):
    model_config = _strip

    book_id: str | None = Field(default=None, description="Omit or null for 'General / Account Level'")
    subject: str = Field(min_length=5, max_length=150)
    description: str = Field(min_length=20, max_length=5000)
    attachment_name: str | None = Field(default=None, max_length=255, description="File name only (UI-level attachment)")


class AuthorMessageCreate(BaseModel):
    model_config = _strip

    body: str = Field(min_length=1, max_length=5000)


class AdminMessageCreate(BaseModel):
    model_config = _strip

    body: str = Field(min_length=1, max_length=8000)
    internal: bool = Field(default=False, description="true = internal note, never shown to the author")
    ai_assisted: bool = Field(default=False, description="Reply started from the AI draft (for metrics)")
    set_status: TicketStatus | None = Field(default=None, description="Optionally change status in the same action")


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus | None = None
    category: Category | None = None
    priority: Priority | None = None
    assigned_to_id: str | None = Field(default=None, description="Admin user id; send null to unassign")

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class DraftRequest(BaseModel):
    regenerate: bool = False


# ---------- Responses ----------


class MessageOut(BaseModel):
    id: str
    kind: MessageKind
    sender_role: Role
    sender_name: str
    body: str
    ai_assisted: bool = False
    created_at: datetime


class AssigneeOut(BaseModel):
    id: str
    name: str


class AuthorTicketOut(BaseModel):
    """What an author sees. No priority, no AI internals, no internal notes."""

    ticket_number: int
    subject: str
    description: str
    attachment_name: str | None
    status: TicketStatus
    category: Category
    book: BookRef | None
    messages: list[MessageOut]
    unread_reply: bool = Field(description="BookLeaf replied since the author last opened this ticket")
    created_at: datetime
    updated_at: datetime


class AiTriageOut(BaseModel):
    category: Category | None = None
    priority: Priority | None = None
    reason: str | None = None
    model: str | None = None


class AdminTicketSummary(BaseModel):
    """One row in the admin queue."""

    ticket_number: int
    subject: str
    author_id: str
    author_name: str
    book: BookRef | None
    status: TicketStatus
    category: Category
    priority: Priority
    classified_by: ClassifiedBy
    assigned_to: AssigneeOut | None
    message_count: int
    awaiting_reply: bool  # last visible message is from the author
    sla_breached: bool  # unresolved and first response is overdue for its priority
    created_at: datetime
    updated_at: datetime


class AuthorProfileOut(BaseModel):
    author_id: str
    name: str
    email: str
    phone: str | None
    city: str | None
    joined_date: str | None


class AdminTicketDetail(AdminTicketSummary):
    description: str
    attachment_name: str | None
    ai: AiTriageOut | None
    messages: list[MessageOut]  # includes internal notes
    author: AuthorProfileOut
    book_details: BookOut | None
    author_books: list[BookOut]  # context for general/account-level tickets
    first_response_at: datetime | None
    resolved_at: datetime | None


class DraftOut(BaseModel):
    text: str
    model: str
    generated_at: datetime
    cached: bool


class TicketStats(BaseModel):
    by_status: dict[str, int]
    unresolved_by_priority: dict[str, int]
    unassigned_unresolved: int
    sla_breached: int
    ai: dict  # calls, failures, tokens over the last 7 days + override rate
