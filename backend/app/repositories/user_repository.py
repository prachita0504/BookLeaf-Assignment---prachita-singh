"""MongoDB queries for the 'users' collection (authors and admins)."""

from pymongo import ReturnDocument

from app.core.database import Collections, get_db
from app.schemas.common import Role


def _users():
    return get_db()[Collections.USERS]


async def find_by_email(email: str) -> dict | None:
    return await _users().find_one({"email": email.lower()})


async def find_by_id(user_id: str) -> dict | None:
    return await _users().find_one({"_id": user_id})


async def find_by_author_id(author_id: str) -> dict | None:
    return await _users().find_one({"author_id": author_id})


async def find_by_author_ids(author_ids: list[str]) -> dict[str, dict]:
    docs = await _users().find({"author_id": {"$in": author_ids}}).to_list()
    return {d["author_id"]: d for d in docs}


async def insert(user: dict) -> None:
    await _users().insert_one(user)


async def next_author_id() -> str:
    """Next free id in the dataset's format (AUTH011, AUTH012, ...). Atomic counter, skipping any
    id that's already taken (e.g. if the counter was reset)."""
    while True:
        counter = await get_db()[Collections.COUNTERS].find_one_and_update(
            {"_id": "author_id"}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
        )
        author_id = f"AUTH{counter['seq']:03d}"
        if not await _users().find_one({"author_id": author_id}, {"_id": 1}):
            return author_id


async def list_admins() -> list[dict]:
    return await _users().find({"role": Role.ADMIN}, {"password_hash": 0}).sort("name").to_list()
