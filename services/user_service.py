"""Service métier pour les opérations sur l'utilisateur courant."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import security
from models.user import User
from schemas.user import ChangePasswordIn, UpdatePseudoIn


class UserError(Exception):
    """Base."""


class PseudoAlreadyTakenError(UserError):
    pass


class WrongCurrentPasswordError(UserError):
    pass


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def update_pseudo(self, user: User, data: UpdatePseudoIn) -> User:
        # If requested pseudo is same as current, no-op
        if data.pseudo == user.pseudo:
            return user

        # Check it's not taken by another user (citext → case-insensitive)
        existing = (
            await self._session.execute(
                select(User.id).where(User.pseudo == data.pseudo, User.id != user.id)
            )
        ).first()
        if existing:
            raise PseudoAlreadyTakenError(data.pseudo)

        user.pseudo = data.pseudo
        await self._session.flush()
        return user

    async def change_password(self, user: User, data: ChangePasswordIn) -> None:
        if not security.verify_password(data.current_password, user.password_hash):
            raise WrongCurrentPasswordError()
        user.password_hash = security.hash_password(data.new_password)
        await self._session.flush()
