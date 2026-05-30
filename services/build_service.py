"""Service métier pour les builds (CRUD avec ownership checks)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import cast, delete as sql_delete, or_, select
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.types import Text
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


@dataclass
class ForkedFromRow:
    id: object
    name: str
    author_pseudo: str


@dataclass
class PublicBuildRow:
    id: object
    name: str
    description: str | None
    tags: list
    like_count: int
    created_at: object
    author_pseudo: str
    liked_by_me: bool
    intent: str


@dataclass
class PublicBuildDetailRow:
    id: object
    name: str
    description: str | None
    data: dict
    tags: list
    like_count: int
    created_at: object
    updated_at: object
    author_pseudo: str
    liked_by_me: bool
    is_mine: bool
    intent: str
    forked_from: ForkedFromRow | None


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
            tags=data.tags,
            intent=data.intent,
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

    async def list_public(
        self, viewer, search, tags, sort: str, limit: int, offset: int
    ) -> list[PublicBuildRow]:
        from models.build_like import BuildLike
        from models.user import User as _User

        stmt = (
            select(Build, _User.pseudo.label("author_pseudo"))
            .join(_User, _User.id == Build.user_id)
            .where(Build.is_public.is_(True))
        )
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(Build.name.ilike(like), _User.pseudo.ilike(like)))
        if tags:
            stmt = stmt.where(Build.tags.op("@>")(cast(tags, PG_ARRAY(Text))))
        if sort == "popular":
            stmt = stmt.order_by(Build.like_count.desc(), Build.created_at.desc())
        else:
            stmt = stmt.order_by(Build.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        records = (await self._session.execute(stmt)).all()

        liked_ids: set = set()
        if viewer is not None and records:
            ids = [b.id for b, _ in records]
            liked = await self._session.execute(
                select(BuildLike.build_id).where(
                    BuildLike.user_id == viewer.id, BuildLike.build_id.in_(ids)
                )
            )
            liked_ids = {r[0] for r in liked.all()}

        return [
            PublicBuildRow(
                id=b.id, name=b.name, description=b.description, tags=list(b.tags),
                like_count=b.like_count, created_at=b.created_at,
                author_pseudo=author_pseudo, liked_by_me=b.id in liked_ids,
                intent=b.intent,
            )
            for b, author_pseudo in records
        ]

    async def get_public(self, viewer, build_id) -> PublicBuildDetailRow:
        from models.build_like import BuildLike
        from models.user import User as _User

        build = await self._session.get(Build, build_id)
        if build is None:
            raise BuildNotFoundError(str(build_id))
        is_owner = viewer is not None and build.user_id == viewer.id
        if not build.is_public and not is_owner:
            raise BuildNotFoundError(str(build_id))

        author_pseudo = (
            await self._session.execute(select(_User.pseudo).where(_User.id == build.user_id))
        ).scalar_one()

        liked_by_me = False
        if viewer is not None:
            liked_by_me = (
                await self._session.execute(
                    select(BuildLike.id).where(
                        BuildLike.user_id == viewer.id, BuildLike.build_id == build.id
                    )
                )
            ).first() is not None

        forked_from = None
        if build.forked_from_id is not None:
            src = await self._session.get(Build, build.forked_from_id)
            if src is not None:
                src_author = (
                    await self._session.execute(select(_User.pseudo).where(_User.id == src.user_id))
                ).scalar_one()
                forked_from = ForkedFromRow(id=src.id, name=src.name, author_pseudo=src_author)

        return PublicBuildDetailRow(
            id=build.id, name=build.name, description=build.description, data=build.data,
            tags=list(build.tags), like_count=build.like_count,
            created_at=build.created_at, updated_at=build.updated_at,
            author_pseudo=author_pseudo, liked_by_me=liked_by_me, is_mine=is_owner,
            intent=build.intent,
            forked_from=forked_from,
        )

    async def like(self, user, build_id) -> tuple[bool, int]:
        """Like idempotent d'un build public. Renvoie (liked, like_count)."""
        from models.build_like import BuildLike

        build = await self._session.get(Build, build_id)
        if build is None or not build.is_public:
            raise BuildNotFoundError(str(build_id))

        existing = (
            await self._session.execute(
                select(BuildLike.id).where(
                    BuildLike.user_id == user.id, BuildLike.build_id == build_id
                )
            )
        ).first()
        if existing is None:
            self._session.add(BuildLike(user_id=user.id, build_id=build_id))
            build.like_count += 1
            await self._session.flush()
        return True, build.like_count

    async def unlike(self, user, build_id) -> tuple[bool, int]:
        """Unlike idempotent. Renvoie (liked, like_count)."""
        from models.build_like import BuildLike

        build = await self._session.get(Build, build_id)
        if build is None or not build.is_public:
            raise BuildNotFoundError(str(build_id))

        result = await self._session.execute(
            sql_delete(BuildLike).where(
                BuildLike.user_id == user.id, BuildLike.build_id == build_id
            )
        )
        if result.rowcount and build.like_count > 0:
            build.like_count -= 1
            await self._session.flush()
        return False, build.like_count

    async def fork(self, user, build_id) -> Build:
        source = await self._session.get(Build, build_id)
        if source is None:
            raise BuildNotFoundError(str(build_id))
        is_owner = source.user_id == user.id
        if not source.is_public and not is_owner:
            raise BuildNotFoundError(str(build_id))
        fork = Build(
            user_id=user.id,
            name=f"{source.name} (copy)"[:100],
            description=source.description,
            data=source.data,
            is_public=False,
            tags=list(source.tags),
            forked_from_id=source.id,
            intent=source.intent,
        )
        self._session.add(fork)
        await self._session.flush()
        return fork
