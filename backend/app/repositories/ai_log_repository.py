"""Writes one record per LLM call (model, tokens, latency, success) for cost and reliability tracking."""

from datetime import timedelta
from uuid import uuid4

from app.core.database import Collections, get_db
from app.utils.dates import utcnow


def _logs():
    return get_db()[Collections.AI_CALL_LOGS]


async def log_call(
    *,
    task: str,
    model: str,
    success: bool,
    ticket_number: int | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    error: str | None = None,
) -> None:
    await _logs().insert_one(
        {
            "_id": uuid4().hex,
            "task": task,
            "model": model,
            "success": success,
            "ticket_number": ticket_number,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "error": error,
            "created_at": utcnow(),
        }
    )


async def usage_summary(days: int = 7) -> dict:
    since = utcnow() - timedelta(days=days)
    cursor = await _logs().aggregate(
        [
            {"$match": {"created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": "$task",
                    "calls": {"$sum": 1},
                    "failures": {"$sum": {"$cond": ["$success", 0, 1]}},
                    "prompt_tokens": {"$sum": "$prompt_tokens"},
                    "completion_tokens": {"$sum": "$completion_tokens"},
                    "avg_latency_ms": {"$avg": "$latency_ms"},
                }
            },
        ]
    )
    rows = await cursor.to_list()
    return {
        r["_id"]: {
            "calls": r["calls"],
            "failures": r["failures"],
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
            "avg_latency_ms": round(r["avg_latency_ms"] or 0),
        }
        for r in rows
    }
