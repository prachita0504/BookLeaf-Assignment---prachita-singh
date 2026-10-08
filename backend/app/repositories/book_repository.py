"""MongoDB queries for the 'books' collection."""

from app.core.database import Collections, get_db


def _books():
    return get_db()[Collections.BOOKS]


async def list_by_author(author_id: str) -> list[dict]:
    return await _books().find({"author_id": author_id}).sort("_id").to_list()


async def find_by_id(book_id: str) -> dict | None:
    return await _books().find_one({"_id": book_id})


async def find_for_author(book_id: str, author_id: str) -> dict | None:
    """Ownership-checked lookup: returns None if the book belongs to someone else."""
    return await _books().find_one({"_id": book_id, "author_id": author_id})


async def find_by_ids(book_ids: list[str]) -> dict[str, dict]:
    docs = await _books().find({"_id": {"$in": book_ids}}).to_list()
    return {d["_id"]: d for d in docs}
