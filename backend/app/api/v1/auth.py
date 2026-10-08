"""Auth routes: POST /auth/login, POST /auth/register, POST /auth/logout, GET /auth/me."""

from fastapi import APIRouter, Response, status

from app.api.deps import AnyUser
from app.core.config import get_settings
from app.core.security import SESSION_COOKIE
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserOut
from app.services import auth_service

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="Log in with email and password")
async def login(body: LoginRequest, response: Response) -> LoginResponse:
    result = await auth_service.login(body.email, body.password)
    _set_session_cookie(response, result.access_token)
    return result


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up as a new author (logs in immediately)",
    responses={409: {"description": "Email already registered"}},
)
async def register(body: RegisterRequest, response: Response) -> LoginResponse:
    result = await auth_service.register(body)
    _set_session_cookie(response, result.access_token)
    return result


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,  # not readable by JavaScript, so XSS can't steal the session
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Clear the session cookie")
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut, summary="The currently logged-in user")
async def me(user: AnyUser) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role, author_id=user.author_id)
