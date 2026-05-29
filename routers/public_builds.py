"""Endpoints publics de builds (sans auth obligatoire). PR5a."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_deps import get_current_user, get_current_user_optional
from core.db import get_session
from models.user import User
from schemas.build import LikeStatus, PublicBuildListItem, PublicBuildOut
from services.build_service import BuildNotFoundError, BuildService

router = APIRouter()


@router.get("/builds", response_model=list[PublicBuildListItem])
async def list_public_builds(
    search: str | None = Query(default=None),
    tags: str | None = Query(default=None, description="CSV de tags"),
    sort: str = Query(default="recent", pattern="^(recent|popular)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    viewer: User | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[PublicBuildListItem]:
    tag_list = [t for t in (tags.split(",") if tags else []) if t]
    svc = BuildService(session)
    rows = await svc.list_public(
        viewer=viewer, search=search, tags=tag_list or None, sort=sort, limit=limit, offset=offset
    )
    return [PublicBuildListItem.model_validate(r) for r in rows]


@router.get("/builds/{build_id}", response_model=PublicBuildOut)
async def get_public_build(
    build_id: uuid.UUID,
    viewer: User | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> PublicBuildOut:
    svc = BuildService(session)
    try:
        row = await svc.get_public(viewer=viewer, build_id=build_id)
    except BuildNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Build not found")
    return PublicBuildOut.model_validate(row)


@router.post("/builds/{build_id}/like", response_model=LikeStatus)
async def like_build(
    build_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LikeStatus:
    svc = BuildService(session)
    try:
        liked, count = await svc.like(user=user, build_id=build_id)
    except BuildNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Build not found")
    await session.commit()
    return LikeStatus(liked=liked, like_count=count)


@router.delete("/builds/{build_id}/like", response_model=LikeStatus)
async def unlike_build(
    build_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LikeStatus:
    svc = BuildService(session)
    try:
        liked, count = await svc.unlike(user=user, build_id=build_id)
    except BuildNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Build not found")
    await session.commit()
    return LikeStatus(liked=liked, like_count=count)
