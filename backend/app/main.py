"""FastAPI application entry point.

Run locally:  uvicorn app.main:app --reload   (from the backend/ folder)
Swagger docs: http://localhost:8000/docs

If the React app has been built (frontend/dist), it is served from the same server, so the whole
product runs from one URL and one process. In development the Vite dev server is used instead.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core import database
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, register_exception_handlers
from app.core.logging import setup_logging

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.connect()
    yield
    await database.disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(debug=not settings.is_production)

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="REST API for the BookLeaf Author Support & Communication Portal.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,  # needed for the httpOnly session cookie
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built single-page app. Unknown non-API paths return index.html so client-side
    routes like /tickets/1001 work on a page refresh."""
    if not (FRONTEND_DIST / "index.html").exists():
        return
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            raise NotFoundError("API route not found")
        file = (FRONTEND_DIST / path).resolve()
        if path and file.is_file() and FRONTEND_DIST in file.parents:
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")


app = create_app()
