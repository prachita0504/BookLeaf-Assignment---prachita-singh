"""Author book listing and derived royalty facts (e.g. below ₹1,000 payout threshold)."""

from app.repositories import book_repository
from app.schemas.book import BookOut


async def list_author_books(author_id: str) -> list[BookOut]:
    books = [BookOut.from_doc(doc) for doc in await book_repository.list_by_author(author_id)]
    # Published books first (newest first), then books still in production.
    return sorted(books, key=lambda b: (not b.is_published, -(b.publication_date.toordinal() if b.publication_date else 0)))
