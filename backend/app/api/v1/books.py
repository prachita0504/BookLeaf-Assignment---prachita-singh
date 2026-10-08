"""Author book routes: GET /books (the logged-in author's books only)."""

from fastapi import APIRouter

from app.api.deps import AuthorUser
from app.schemas.book import BookOut
from app.services import book_service

router = APIRouter()


@router.get("", response_model=list[BookOut], summary="List my books with sales and royalty details")
async def list_my_books(user: AuthorUser) -> list[BookOut]:
    return await book_service.list_author_books(user.author_id)
