"""Endpoints /users/* (PR3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_deps import get_current_user
from core.db import get_session
from models.user import User
from schemas.auth import UserOut
from schemas.user import ChangePasswordIn, UpdatePseudoIn
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
