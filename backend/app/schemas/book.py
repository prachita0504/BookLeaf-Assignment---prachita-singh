"""Book response model, plus a few derived fields so the UI doesn't re-implement business rules."""

from datetime import date

from pydantic import BaseModel

from app.schemas.common import MIN_PAYOUT_THRESHOLD, PRODUCTION_STAGES


class BookOut(BaseModel):
    id: str
    title: str
    isbn: str
    genre: str
    publication_date: date | None
    status: str
    mrp: int | None
    author_royalty_per_copy: int | None
    total_copies_sold: int
    total_royalty_earned: int
    royalty_paid: int
    royalty_pending: int
    last_royalty_payout_date: date | None
    print_partner: str | None
    available_on: list[str]

    # Derived
    is_published: bool
    production_stage: str  # e.g. "Cover Design", or "Published & Live"
    production_stage_index: int  # position in PRODUCTION_STAGES (for a progress tracker)
    below_payout_threshold: bool  # pending > 0 but under ₹1,000: rolls over to next quarter

    @classmethod
    def from_doc(cls, doc: dict) -> "BookOut":
        status: str = doc["status"]
        stage = status.split(" - ", 1)[1] if status.startswith("In Production - ") else status
        pending = doc.get("royalty_pending") or 0
        return cls(
            id=doc["_id"],
            title=doc["title"],
            isbn=doc["isbn"],
            genre=doc["genre"],
            publication_date=doc.get("publication_date"),
            status=status,
            mrp=doc.get("mrp"),
            author_royalty_per_copy=doc.get("author_royalty_per_copy"),
            total_copies_sold=doc.get("total_copies_sold") or 0,
            total_royalty_earned=doc.get("total_royalty_earned") or 0,
            royalty_paid=doc.get("royalty_paid") or 0,
            royalty_pending=pending,
            last_royalty_payout_date=doc.get("last_royalty_payout_date"),
            print_partner=doc.get("print_partner"),
            available_on=doc.get("available_on") or [],
            is_published=status == "Published & Live",
            production_stage=stage,
            production_stage_index=PRODUCTION_STAGES.index(stage) if stage in PRODUCTION_STAGES else 0,
            below_payout_threshold=0 < pending < MIN_PAYOUT_THRESHOLD,
        )


class BookRef(BaseModel):
    """Compact book info embedded in ticket responses."""

    id: str
    title: str
    isbn: str
    status: str
