"""Pydantic schemas pour les endpoints /builds/*."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BuildCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    data: dict[str, Any]
    is_public: bool = False


class BuildUpdateIn(BaseModel):
    """All fields optional — PATCH semantics (None = no change)."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    data: dict[str, Any] | None = None
    is_public: bool | None = None


class BuildListItem(BaseModel):
    """Compact view for lists (no JSONB data which can be heavy)."""
    id: uuid.UUID
    name: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildOut(BaseModel):
    """Full view (with data)."""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    data: dict[str, Any]
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
