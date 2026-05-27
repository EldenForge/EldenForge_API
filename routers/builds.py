"""Endpoints /builds/* (PR3)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_deps import get_current_user
from core.db import get_session
from models.user import User
from schemas.build import BuildCreateIn, BuildListItem, BuildOut, BuildUpdateIn
from services.build_service import (
    BuildNotFoundError,
    BuildService,
    NotBuildOwnerError,
)

router = APIRouter()


@router.post("", response_model=BuildOut, status_code=status.HTTP_201_CREATED)
async def create_build(
    data: BuildCreateIn,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BuildOut:
    svc = BuildService(session)
    build = await svc.create(current, data)
    await session.commit()
    return BuildOut.model_validate(build)


@router.get("", response_model=list[BuildListItem])
async def list_my_builds(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BuildListItem]:
    svc = BuildService(session)
    builds = await svc.list_for_user(current, limit=limit, offset=offset)
    return [BuildListItem.model_validate(b) for b in builds]


@router.get("/{build_id}", response_model=BuildOut)
async def get_build(
    build_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BuildOut:
    svc = BuildService(session)
    try:
        build = await svc.get_for_viewer(current, build_id)
    except BuildNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Build not found")
    return BuildOut.model_validate(build)


@router.put("/{build_id}", response_model=BuildOut)
async def update_build(
    build_id: uuid.UUID,
    data: BuildUpdateIn,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BuildOut:
    svc = BuildService(session)
    try:
        build = await svc.update(current, build_id, data)
    except BuildNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Build not found")
    except NotBuildOwnerError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your build")
    await session.commit()
    await session.refresh(build)
    return BuildOut.model_validate(build)


@router.delete("/{build_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_build(
    build_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = BuildService(session)
    try:
        await svc.delete(current, build_id)
    except BuildNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Build not found")
    except NotBuildOwnerError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your build")
    await session.commit()
