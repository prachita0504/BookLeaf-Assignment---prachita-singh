"""GET /api/v1/health: liveness check used by the frontend setup page and the hosting platform."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    db_ok = True
    try:
        await get_db().command("ping")
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        # Reports only whether AI is configured, never the key itself.
        "ai": "enabled" if get_settings().ai_enabled else "fallback-only",
    }
