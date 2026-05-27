"""Dépendances FastAPI pour récupérer l'utilisateur courant depuis le cookie JWT."""
from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core import security
from core.db import get_session
from models.user import User


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Lit le cookie access_token, valide le JWT, retourne le User. 401 sinon."""
    if access_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        user_id = security.decode_access_token(access_token)
    except security.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


async def get_current_user_optional(
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Variante qui retourne None plutôt que 401 si pas authentifié."""
    if access_token is None:
        return None
    try:
        return await get_current_user(access_token=access_token, session=session)
    except HTTPException:
        return None
