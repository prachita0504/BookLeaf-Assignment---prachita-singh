"""Verifies credentials, registers new authors and builds the session for a user."""

from uuid import uuid4

from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import user_repository
from app.schemas.auth import LoginResponse, RegisterRequest, UserOut
from app.schemas.common import Role
from app.utils.dates import utcnow


def to_user_out(user: dict) -> UserOut:
    return UserOut(
        id=user["_id"], name=user["name"], email=user["email"], role=user["role"], author_id=user.get("author_id")
    )


def _session(user: dict) -> LoginResponse:
    token = create_access_token(
        {"sub": user["_id"], "role": user["role"], "name": user["name"], "email": user["email"],
         "author_id": user.get("author_id")}
    )
    return LoginResponse(user=to_user_out(user), access_token=token)


async def login(email: str, password: str) -> LoginResponse:
    user = await user_repository.find_by_email(email)
    # verify_password runs even when the user doesn't exist (same timing, no account enumeration).
    if not verify_password(password, user["password_hash"] if user else None) or not user:
        raise UnauthorizedError("Invalid email or password")
    return _session(user)


async def register(data: RegisterRequest) -> LoginResponse:
    """Creates a new AUTHOR account (no books yet) and logs them in."""
    email = data.email.lower()
    if await user_repository.find_by_email(email):
        raise ConflictError("An account with this email already exists. Please log in instead.")

    user = {
        "_id": f"user-{uuid4().hex[:12]}",
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": Role.AUTHOR,
        "author_id": await user_repository.next_author_id(),
        "phone": data.phone or None,
        "city": data.city or None,
        "joined_date": utcnow().date().isoformat(),
        "created_at": utcnow(),
    }
    try:
        await user_repository.insert(user)
    except DuplicateKeyError:  # two sign-ups with the same email at the same moment
        raise ConflictError("An account with this email already exists. Please log in instead.")
    return _session(user)
