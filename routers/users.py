"""Endpoints /users/* (PR3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_deps import get_current_user
from core.db import get_session
from models.user import User
from schemas.auth import UserOut
from schemas.build import PublicBuildListItem
from schemas.user import ChangePasswordIn, UpdatePseudoIn
from services.build_service import BuildService
from services.user_service import (
    PseudoAlreadyTakenError,
    UserService,
    WrongCurrentPasswordError,
)

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UpdatePseudoIn,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    svc = UserService(session)
    try:
        updated = await svc.update_pseudo(current, data)
    except PseudoAlreadyTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pseudo already taken")
    await session.commit()
    await session.refresh(updated)
    return UserOut.model_validate(updated)


@router.get("/me/likes", response_model=list[PublicBuildListItem])
async def list_my_likes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PublicBuildListItem]:
    svc = BuildService(session)
    rows = await svc.list_liked_by_user(current, limit=limit, offset=offset)
    return [PublicBuildListItem.model_validate(r) for r in rows]


@router.post("/me/password")
async def change_my_password(
    data: ChangePasswordIn,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    svc = UserService(session)
    try:
        await svc.change_password(current, data)
    except WrongCurrentPasswordError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")
    await session.commit()
    return {"ok": True}
