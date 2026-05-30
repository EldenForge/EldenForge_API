"""Pydantic schemas pour les endpoints /builds/*."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


BuildIntent = Literal["pve", "coop", "pvp"]


ALLOWED_TAGS: list[str] = [
    "Strength", "Dexterity", "Intelligence", "Faith", "Arcane", "Quality",
    "Bleed", "Sorceries", "Incantations", "Poison", "Frost", "Lightning", "Fire",
    "PvP", "PvE", "Boss", "Beginner", "End-game", "No-hit",
]
_ALLOWED_TAGS_SET = set(ALLOWED_TAGS)


def _validate_tags(tags: list[str]) -> list[str]:
    unknown = [t for t in tags if t not in _ALLOWED_TAGS_SET]
    if unknown:
        raise ValueError(f"Unknown tags: {unknown}. Allowed: {ALLOWED_TAGS}")
    seen: set[str] = set()
    return [t for t in tags if not (t in seen or seen.add(t))]


class BuildCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    data: dict[str, Any]
    is_public: bool = False
    tags: list[str] = Field(default_factory=list)
    intent: BuildIntent = "pve"

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v: list[str]) -> list[str]:
        return _validate_tags(v)


class BuildUpdateIn(BaseModel):
    """All fields optional — PATCH semantics (None = no change)."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    data: dict[str, Any] | None = None
    is_public: bool | None = None
    tags: list[str] | None = None
    intent: BuildIntent | None = None

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v: list[str] | None) -> list[str] | None:
        return _validate_tags(v) if v is not None else None


class BuildListItem(BaseModel):
    """Compact view for lists (no JSONB data which can be heavy)."""
    id: uuid.UUID
    name: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    intent: BuildIntent = "pve"

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
    tags: list[str] = Field(default_factory=list)
    forked_from_id: uuid.UUID | None = None
    intent: BuildIntent = "pve"

    model_config = ConfigDict(from_attributes=True)


class PublicBuildListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    tags: list[str]
    like_count: int
    created_at: datetime
    author_pseudo: str
    liked_by_me: bool = False
    intent: BuildIntent = "pve"
    primary_weapon_image: str | None = None
    has_dlc: bool = False

    model_config = ConfigDict(from_attributes=True)


class ForkedFromInfo(BaseModel):
    id: uuid.UUID
    name: str
    author_pseudo: str

    model_config = ConfigDict(from_attributes=True)


class PublicBuildOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    data: dict
    tags: list[str]
    like_count: int
    created_at: datetime
    updated_at: datetime
    author_pseudo: str
    liked_by_me: bool = False
    is_mine: bool = False
    intent: BuildIntent = "pve"
    forked_from: ForkedFromInfo | None = None
    has_dlc: bool = False

    model_config = ConfigDict(from_attributes=True)


class LikeStatus(BaseModel):
    liked: bool
    like_count: int
