"""Aggregates all v1 routers."""

from fastapi import APIRouter

from app.api.v1 import admin_tickets, auth, books, health, tickets

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(books.router, prefix="/books", tags=["Author: Books"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Author: Tickets"])
api_router.include_router(admin_tickets.router, prefix="/admin", tags=["Admin"])
