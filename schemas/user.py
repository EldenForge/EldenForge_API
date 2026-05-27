"""Pydantic schemas pour les endpoints /users/me."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from schemas.auth import PSEUDO_PATTERN, _validate_password_strength


class UpdatePseudoIn(BaseModel):
    pseudo: str = Field(min_length=3, max_length=30, pattern=PSEUDO_PATTERN)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)
