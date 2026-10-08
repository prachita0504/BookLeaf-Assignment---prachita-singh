"""Shared enums and constants. The single source of truth for allowed values across API, DB and AI."""

from enum import StrEnum


class Role(StrEnum):
    AUTHOR = "AUTHOR"
    ADMIN = "ADMIN"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


UNRESOLVED_STATUSES = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS)


class Category(StrEnum):
    ROYALTY_PAYMENTS = "ROYALTY_PAYMENTS"
    ISBN_METADATA = "ISBN_METADATA"
    PRINTING_QUALITY = "PRINTING_QUALITY"
    DISTRIBUTION = "DISTRIBUTION"
    PRODUCTION_STATUS = "PRODUCTION_STATUS"
    GENERAL = "GENERAL"


CATEGORY_LABELS: dict[Category, str] = {
    Category.ROYALTY_PAYMENTS: "Royalty & Payments",
    Category.ISBN_METADATA: "ISBN & Metadata Issues",
    Category.PRINTING_QUALITY: "Printing & Quality",
    Category.DISTRIBUTION: "Distribution & Availability",
    Category.PRODUCTION_STATUS: "Book Status & Production Updates",
    Category.GENERAL: "General Inquiry",
}


class Priority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Lower = more urgent. Stored on the ticket so MongoDB can sort the queue by urgency.
PRIORITY_RANK: dict[Priority, int] = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}

# First-response targets in hours. Unanswered tickets older than this are flagged in the admin queue.
RESPONSE_SLA_HOURS: dict[Priority, int] = {Priority.CRITICAL: 4, Priority.HIGH: 24, Priority.MEDIUM: 48, Priority.LOW: 72}


class ClassifiedBy(StrEnum):
    RULES = "RULES"  # instant keyword fallback
    AI = "AI"  # LLM classification
    ADMIN = "ADMIN"  # human override, which the AI never overwrites


class MessageKind(StrEnum):
    REPLY = "REPLY"  # visible to the author
    NOTE = "NOTE"  # internal, admin-only


PRODUCTION_STAGES = [
    "Manuscript Received",
    "Editing",
    "Cover Design",
    "Typesetting",
    "Proofreading",
    "ISBN Assignment",
    "Printing",
    "Distribution Setup",
    "Published & Live",
]

MIN_PAYOUT_THRESHOLD = 1000  # ₹
