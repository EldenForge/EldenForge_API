"""Service métier pour les builds (CRUD avec ownership checks)."""
from __future__ import annotations

import uuid

from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.build import Build
from models.user import User
from schemas.build import BuildCreateIn, BuildUpdateIn


class BuildError(Exception):
    """Base."""


class BuildNotFoundError(BuildError):
    pass


class NotBuildOwnerError(BuildError):
    """L'utilisateur n'est pas propriétaire du build (403)."""


class BuildService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User, data: BuildCreateIn) -> Build:
        build = Build(
            user_id=user.id,
            name=data.name,
            description=data.description,
            data=data.data,
            is_public=data.is_public,
        )
        self._session.add(build)
        await self._session.flush()
        return build

    async def list_for_user(self, user: User, limit: int, offset: int) -> list[Build]:
        result = await self._session.execute(
            select(Build)
            .where(Build.user_id == user.id)
            .order_by(Build.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_for_viewer(self, viewer: User, build_id: uuid.UUID) -> Build:
        """Returns the build if visible by viewer (owner OR is_public). 404 otherwise."""
        build = await self._session.get(Build, build_id)
        if build is None:
            raise BuildNotFoundError(str(build_id))
        if build.user_id != viewer.id and not build.is_public:
            # 404 not 403 — don't leak existence of others' private builds
            raise BuildNotFoundError(str(build_id))
        return build

    async def update(self, user: User, build_id: uuid.UUID, data: BuildUpdateIn) -> Build:
        build = await self._session.get(Build, build_id)
        if build is None:
            raise BuildNotFoundError(str(build_id))
        if build.user_id != user.id:
            raise NotBuildOwnerError(str(build_id))

        # PATCH semantics — only apply fields explicitly set
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(build, key, value)
        await self._session.flush()
        return build

    async def delete(self, user: User, build_id: uuid.UUID) -> None:
        build = await self._session.get(Build, build_id)
        if build is None:
            raise BuildNotFoundError(str(build_id))
        if build.user_id != user.id:
            raise NotBuildOwnerError(str(build_id))
        await self._session.execute(sql_delete(Build).where(Build.id == build_id))
        await self._session.flush()
