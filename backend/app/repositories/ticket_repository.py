"""MongoDB queries for the 'tickets' collection, incl. queue filtering/sorting and ticket numbers.

A ticket's `_id` is its human-friendly number (1001, 1002, ...), so URLs read /tickets/1042.
Messages are embedded in the ticket document (small, always read together, updated atomically).
"""

from datetime import datetime
from re import escape

from pymongo import ReturnDocument

from app.core.database import Collections, get_db
from app.schemas.common import UNRESOLVED_STATUSES, ClassifiedBy, MessageKind
from app.utils.dates import utcnow

FIRST_TICKET_NUMBER = 1001
QUEUE_LIMIT = 200


def _tickets():
    return get_db()[Collections.TICKETS]


async def next_ticket_number() -> int:
    """Atomic auto-increment (safe under concurrent ticket creation)."""
    counter = await get_db()[Collections.COUNTERS].find_one_and_update(
        {"_id": "ticket_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return FIRST_TICKET_NUMBER - 1 + counter["seq"]


async def insert(doc: dict) -> dict:
    await _tickets().insert_one(doc)
    return doc


async def find(number: int) -> dict | None:
    return await _tickets().find_one({"_id": number})


async def find_for_author(number: int, author_id: str) -> dict | None:
    """Ownership-checked lookup: another author's ticket looks exactly like a missing one."""
    return await _tickets().find_one({"_id": number, "author_id": author_id})


async def list_for_author(author_id: str) -> list[dict]:
    return await _tickets().find({"author_id": author_id}).sort("updated_at", -1).to_list()


async def list_queue(
    *,
    status: str | None,
    category: str | None,
    priority: str | None,
    assigned_to_id: str | None,
    unassigned: bool,
    created_from: datetime | None,
    created_to: datetime | None,
    search: str | None,
) -> list[dict]:
    """Admin queue. Unresolved tickets first, then most urgent, then oldest, so the most urgent and
    longest-waiting tickets are always at the top."""
    match: dict = {}
    if status == "UNRESOLVED":
        match["status"] = {"$in": list(UNRESOLVED_STATUSES)}
    elif status:
        match["status"] = status
    if category:
        match["category"] = category
    if priority:
        match["priority"] = priority
    if assigned_to_id:
        match["assigned_to.id"] = assigned_to_id
    if unassigned:
        match["assigned_to"] = None
    if created_from or created_to:
        match["created_at"] = {k: v for k, v in (("$gte", created_from), ("$lte", created_to)) if v}
    if search:
        rx = {"$regex": escape(search), "$options": "i"}
        num = int(search) if search.isdigit() else None
        match["$or"] = [{"subject": rx}, {"author_name": rx}, *([{"_id": num}] if num else [])]

    pipeline = [
        {"$match": match},
        {"$addFields": {"_resolved": {"$cond": [{"$in": ["$status", list(UNRESOLVED_STATUSES)]}, 0, 1]}}},
        {"$sort": {"_resolved": 1, "priority_rank": 1, "created_at": 1}},
        {"$limit": QUEUE_LIMIT},
        # The queue doesn't need full threads: keep only what the summary row uses.
        {
            "$project": {
                "description": 0,
                "ai_draft": 0,
                "messages.body": 0,
            }
        },
    ]
    cursor = await _tickets().aggregate(pipeline)
    return await cursor.to_list()


async def update(number: int, set_fields: dict, *, unset: list[str] | None = None) -> dict | None:
    update_doc: dict = {"$set": {**set_fields, "updated_at": utcnow()}}
    if unset:
        update_doc["$unset"] = {f: "" for f in unset}
    return await _tickets().find_one_and_update(
        {"_id": number}, update_doc, return_document=ReturnDocument.AFTER
    )


async def push_message(number: int, message: dict, set_fields: dict | None = None) -> dict | None:
    now = utcnow()
    return await _tickets().find_one_and_update(
        {"_id": number},
        {
            "$push": {"messages": message},
            "$set": {**(set_fields or {}), "updated_at": now, "last_activity_at": now},
        },
        return_document=ReturnDocument.AFTER,
    )


async def apply_ai_classification(number: int, ai: dict, effective: dict) -> None:
    """Store the AI's suggestion; only change the effective category/priority if no admin has
    overridden them in the meantime (the condition is evaluated atomically by MongoDB)."""
    await _tickets().update_one({"_id": number}, {"$set": {"ai": ai}})
    await _tickets().update_one(
        {"_id": number, "classified_by": {"$ne": ClassifiedBy.ADMIN}},
        {"$set": {**effective, "classified_by": ClassifiedBy.AI}},
    )


async def mark_read_by_author(number: int, when: datetime) -> None:
    """Records that the author has seen the latest replies. Deliberately does NOT touch updated_at,
    so reading a ticket doesn't reorder anyone's ticket list."""
    await _tickets().update_one({"_id": number}, {"$set": {"author_last_read_at": when}})


async def save_draft(number: int, draft: dict) -> None:
    await _tickets().update_one({"_id": number}, {"$set": {"ai_draft": draft}})


async def stats() -> dict:
    pipeline = [
        {
            "$facet": {
                "by_status": [{"$group": {"_id": "$status", "n": {"$sum": 1}}}],
                "unresolved_by_priority": [
                    {"$match": {"status": {"$in": list(UNRESOLVED_STATUSES)}}},
                    {"$group": {"_id": "$priority", "n": {"$sum": 1}}},
                ],
                "unassigned_unresolved": [
                    {"$match": {"status": {"$in": list(UNRESOLVED_STATUSES)}, "assigned_to": None}},
                    {"$count": "n"},
                ],
                "unanswered": [
                    {"$match": {"status": {"$in": list(UNRESOLVED_STATUSES)}, "first_response_at": None}},
                    {"$project": {"priority": 1, "created_at": 1}},
                ],
                "overrides": [
                    {"$match": {"ai.category": {"$exists": True}}},
                    {
                        "$group": {
                            "_id": None,
                            "ai_classified": {"$sum": 1},
                            "category_overridden": {
                                "$sum": {"$cond": [{"$ne": ["$ai.category", "$category"]}, 1, 0]}
                            },
                            "priority_overridden": {
                                "$sum": {"$cond": [{"$ne": ["$ai.priority", "$priority"]}, 1, 0]}
                            },
                        }
                    },
                ],
            }
        }
    ]
    cursor = await _tickets().aggregate(pipeline)
    return (await cursor.to_list())[0]


def visible_to_author(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m.get("kind") == MessageKind.REPLY]
