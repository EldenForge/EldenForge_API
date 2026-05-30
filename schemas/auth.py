"""Pydantic schemas pour les endpoints /auth/*."""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PSEUDO_PATTERN = r"^[A-Za-z0-9_.-]+$"


def _validate_password_strength(v: str) -> str:
    if len(v) < 10:
        raise ValueError("Password must be at least 10 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    return v


class RegisterIn(BaseModel):
    email: EmailStr
    pseudo: str = Field(min_length=3, max_length=30, pattern=PSEUDO_PATTERN)
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    pseudo: str
    email_verified_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicUserProfile(BaseModel):
    """Profil utilisateur publique (sans email ni infos sensibles)."""
    pseudo: str
    created_at: datetime
    builds_count: int
    total_likes_received: int


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)
