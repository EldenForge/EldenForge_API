"""Service métier pour les builds (CRUD avec ownership checks)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlalchemy as sa
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


def _iter_item_ids(data):
    """Yield les item-ids referencés dans un payload de build (sans toucher au guide)."""
    if not isinstance(data, dict):
        return
    for key in ("armor", "weapons", "ashes", "ammos"):
        section = data.get(key)
        if isinstance(section, dict):
            for v in section.values():
                if isinstance(v, str):
                    yield v
                elif isinstance(v, list):
                    for x in v:
                        if isinstance(x, str):
                            yield x
    for key in ("talismans", "spells"):
        arr = data.get(key)
        if isinstance(arr, list):
            for x in arr:
                if isinstance(x, str):
                    yield x
    spirit = data.get("spirit")
    if isinstance(spirit, str):
        yield spirit


def _has_dlc_items(data) -> bool:
    return any(s.startswith("sote-") for s in _iter_item_ids(data))


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
    primary_weapon_image: str | None = None
    has_dlc: bool = False


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
    has_dlc: bool = False


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
        self, viewer, search, tags, sort: str, limit: int, offset: int,
        item: str | None = None, author: str | None = None,
    ) -> list[PublicBuildRow]:
        from sqlalchemy import func
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
        if author:
            stmt = stmt.where(_User.pseudo.ilike(f"%{author}%"))
        if tags:
            stmt = stmt.where(Build.tags.op("@>")(cast(tags, PG_ARRAY(Text))))
        if item:
            # Recherche brute dans le JSONB sérialisé : les ids sont uniques,
            # faux positifs très improbables. MVP simple.
            stmt = stmt.where(cast(Build.data, Text).ilike(f"%{item}%"))
        if sort == "popular":
            stmt = stmt.order_by(Build.like_count.desc(), Build.created_at.desc())
        elif sort == "trending":
            # Likes des 7 derniers jours = trending. Outerjoin pour ne pas filtrer
            # les builds sans like récent (ils tombent à 0 en fin de liste).
            recent_likes_subq = (
                select(
                    BuildLike.build_id,
                    func.count(BuildLike.id).label("recent_likes"),
                )
                .where(BuildLike.created_at > func.now() - sa.text("interval '7 days'"))
                .group_by(BuildLike.build_id)
                .subquery()
            )
            stmt = stmt.outerjoin(recent_likes_subq, Build.id == recent_likes_subq.c.build_id)
            stmt = stmt.order_by(
                func.coalesce(recent_likes_subq.c.recent_likes, 0).desc(),
                Build.created_at.desc(),
            )
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

        # Lookup batch des images d'arme primaire (pour le hero visuel des cartes)
        from core import datasets as _datasets
        wpn_ids: set[str] = set()
        for b, _ in records:
            wid = ((b.data or {}).get("weapons") or {}).get("right")
            if isinstance(wid, str) and wid:
                wpn_ids.add(wid)
        img_by_id: dict[str, str] = {}
        if wpn_ids:
            df = _datasets.get("weapons")
            if df is not None:
                sub = df[df["id"].isin(wpn_ids)][["id", "image"]]
                for _, r in sub.iterrows():
                    img_by_id[str(r["id"])] = str(r["image"]) if r["image"] is not None else ""

        return [
            PublicBuildRow(
                id=b.id, name=b.name, description=b.description, tags=list(b.tags),
                like_count=b.like_count, created_at=b.created_at,
                author_pseudo=author_pseudo, liked_by_me=b.id in liked_ids,
                intent=b.intent,
                primary_weapon_image=img_by_id.get(
                    ((b.data or {}).get("weapons") or {}).get("right") or "", None
                ) or None,
                has_dlc=_has_dlc_items(b.data),
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
            has_dlc=_has_dlc_items(build.data),
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
