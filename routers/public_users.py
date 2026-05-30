"""Endpoint public de profil utilisateur (sans auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from models.build import Build
from models.user import User
from schemas.auth import PublicUserProfile

router = APIRouter()


@router.get("/{pseudo}", response_model=PublicUserProfile)
async def get_public_user(
    pseudo: str,
    session: AsyncSession = Depends(get_session),
) -> PublicUserProfile:
    user = (
        await session.execute(select(User).where(User.pseudo == pseudo))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    row = (
        await session.execute(
            select(
                func.count(Build.id),
                func.coalesce(func.sum(Build.like_count), 0),
            ).where(Build.user_id == user.id, Build.is_public.is_(True))
        )
    ).first()
    builds_count = int(row[0]) if row else 0
    total_likes = int(row[1]) if row else 0

    return PublicUserProfile(
        pseudo=user.pseudo,
        created_at=user.created_at,
        builds_count=builds_count,
        total_likes_received=total_likes,
    )
