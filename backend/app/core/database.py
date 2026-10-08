"""MongoDB connection lifecycle and index setup.

One AsyncMongoClient per process (it pools connections internally). It's opened on app
startup and closed on shutdown; see `lifespan` in app/main.py.
"""

import logging

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncMongoClient | None = None


class Collections:
    """Collection names in one place, so a typo can't silently create a new collection."""

    USERS = "users"
    BOOKS = "books"
    TICKETS = "tickets"
    COUNTERS = "counters"  # auto-increment sequence for human-friendly ticket numbers
    AI_CALL_LOGS = "ai_call_logs"


async def connect() -> None:
    global _client
    settings = get_settings()
    _client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000, tz_aware=True)
    await _client.admin.command("ping")
    logger.info("Connected to MongoDB database '%s'", settings.mongodb_db)
    await ensure_indexes()


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def get_db() -> AsyncDatabase:
    if _client is None:
        raise RuntimeError("Database is not connected. Was the app lifespan started?")
    return _client[get_settings().mongodb_db]


async def ensure_indexes() -> None:
    """Indexes match the queries the app actually runs (idempotent: safe on every startup)."""
    db = get_db()
    await db[Collections.USERS].create_index("email", unique=True)
    await db[Collections.BOOKS].create_index("author_id")
    # tickets._id is the ticket number, so it is already unique and indexed.
    await db[Collections.TICKETS].create_index([("author_id", ASCENDING), ("created_at", DESCENDING)])
    # Admin queue: filter by status/priority, oldest first
    await db[Collections.TICKETS].create_index(
        [("status", ASCENDING), ("priority_rank", ASCENDING), ("created_at", ASCENDING)]
    )
    await db[Collections.AI_CALL_LOGS].create_index("created_at")
