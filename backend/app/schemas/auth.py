"""Login request and current-user response models."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    """Self sign-up creates an AUTHOR account only. Admin accounts are never self-registered."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="At least 8 characters")
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=60)


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    author_id: str | None = None


class LoginResponse(BaseModel):
    user: UserOut
    # The session is also set as an httpOnly cookie (used by the web app). The token is returned
    # here too so non-browser clients (Swagger "Authorize", Postman) can send it as a Bearer header.
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    """The authenticated caller, decoded from the session token (see api/deps.py)."""

    id: str
    role: Role
    name: str
    email: str
    author_id: str | None = None
