"""Shared route dependencies: current user + role guards (role-based access control).

The session token is read from the httpOnly cookie (web app) or an `Authorization: Bearer` header
(Swagger / Postman). Every route except login and health depends on one of these guards.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import SESSION_COOKIE, decode_access_token
from app.schemas.auth import CurrentUser
from app.schemas.common import Role

# auto_error=False: a missing header is fine when the cookie is present. This also adds the
# "Authorize" button to Swagger UI.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> CurrentUser:
    token = credentials.credentials if credentials else request.cookies.get(SESSION_COOKIE)
    if not token:
        raise UnauthorizedError("Please log in to continue")
    claims = decode_access_token(token)
    return CurrentUser(
        id=claims["sub"],
        role=claims["role"],
        name=claims["name"],
        email=claims["email"],
        author_id=claims.get("author_id"),
    )


async def require_author(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role != Role.AUTHOR or not user.author_id:
        raise ForbiddenError("This area is for authors only")
    return user


async def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role != Role.ADMIN:
        raise ForbiddenError("This area is for BookLeaf staff only")
    return user


# Shorthand for route signatures, e.g. `def list_books(user: AuthorUser)`.
AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
AuthorUser = Annotated[CurrentUser, Depends(require_author)]
AdminUser = Annotated[CurrentUser, Depends(require_admin)]
