import uuid

import pytest
from sqlalchemy import select

from models.build import Build
from models.user import User
from schemas.build import BuildCreateIn
from services.build_service import BuildNotFoundError, BuildService


async def _user(session, email, pseudo):
    u = User(email=email, pseudo=pseudo, password_hash="$argon2id$h")
    session.add(u)
    await session.flush()
    return u


async def test_create_persists_tags(db_session):
    u = await _user(db_session, "a@x.com", "A")
    svc = BuildService(db_session)
    b = await svc.create(u, BuildCreateIn(name="B", data={}, tags=["Strength", "Boss"]))
    assert b.tags == ["Strength", "Boss"]


async def test_list_public_only_public(db_session):
    u = await _user(db_session, "a@x.com", "Author")
    svc = BuildService(db_session)
    await svc.create(u, BuildCreateIn(name="pub1", data={}, is_public=True))
    await svc.create(u, BuildCreateIn(name="priv", data={}, is_public=False))
    rows = await svc.list_public(viewer=None, search=None, tags=None, sort="recent", limit=20, offset=0)
    names = {r.name for r in rows}
    assert "pub1" in names and "priv" not in names


async def test_list_public_search_by_name_and_author(db_session):
    u = await _user(db_session, "a@x.com", "Margit")
    svc = BuildService(db_session)
    await svc.create(u, BuildCreateIn(name="Moonveil mage", data={}, is_public=True))
    await svc.create(u, BuildCreateIn(name="Bonk build", data={}, is_public=True))
    by_name = await svc.list_public(viewer=None, search="moonveil", tags=None, sort="recent", limit=20, offset=0)
    assert {r.name for r in by_name} == {"Moonveil mage"}
    by_author = await svc.list_public(viewer=None, search="margit", tags=None, sort="recent", limit=20, offset=0)
    assert len(by_author) == 2


async def test_list_public_filter_tags(db_session):
    u = await _user(db_session, "a@x.com", "A")
    svc = BuildService(db_session)
    await svc.create(u, BuildCreateIn(name="str", data={}, is_public=True, tags=["Strength", "PvE"]))
    await svc.create(u, BuildCreateIn(name="mage", data={}, is_public=True, tags=["Intelligence"]))
    rows = await svc.list_public(viewer=None, search=None, tags=["Strength"], sort="recent", limit=20, offset=0)
    assert {r.name for r in rows} == {"str"}


async def test_list_liked_by_user_returns_only_liked_public(db_session):
    from models.build_like import BuildLike
    author = await _user(db_session, "a@x.com", "Author")
    fan = await _user(db_session, "b@x.com", "Fan")
    svc = BuildService(db_session)
    b_pub_liked = await svc.create(author, BuildCreateIn(name="liked", data={}, is_public=True))
    await svc.create(author, BuildCreateIn(name="unliked", data={}, is_public=True))
    b_priv = await svc.create(author, BuildCreateIn(name="privliked", data={}, is_public=False))
    db_session.add(BuildLike(user_id=fan.id, build_id=b_pub_liked.id))
    db_session.add(BuildLike(user_id=fan.id, build_id=b_priv.id))
    await db_session.flush()

    rows = await svc.list_liked_by_user(fan, limit=20, offset=0)
    assert {r.name for r in rows} == {"liked"}
    assert all(r.liked_by_me for r in rows)


async def test_list_liked_by_user_orders_most_recent_first(db_session):
    from models.build_like import BuildLike
    from datetime import datetime, timezone, timedelta
    author = await _user(db_session, "a@x.com", "Author")
    fan = await _user(db_session, "b@x.com", "Fan")
    svc = BuildService(db_session)
    b1 = await svc.create(author, BuildCreateIn(name="first", data={}, is_public=True))
    b2 = await svc.create(author, BuildCreateIn(name="second", data={}, is_public=True))
    now = datetime.now(timezone.utc)
    db_session.add(BuildLike(user_id=fan.id, build_id=b1.id, created_at=now - timedelta(hours=1)))
    db_session.add(BuildLike(user_id=fan.id, build_id=b2.id, created_at=now))
    await db_session.flush()

    rows = await svc.list_liked_by_user(fan, limit=20, offset=0)
    assert [r.name for r in rows] == ["second", "first"]


async def test_get_public_404_if_private_other(db_session):
    author = await _user(db_session, "a@x.com", "A")
    other = await _user(db_session, "b@x.com", "B")
    svc = BuildService(db_session)
    b = await svc.create(author, BuildCreateIn(name="secret", data={}, is_public=False))
    with pytest.raises(BuildNotFoundError):
        await svc.get_public(viewer=other, build_id=b.id)


async def test_get_public_ok_if_public(db_session):
    author = await _user(db_session, "a@x.com", "A")
    svc = BuildService(db_session)
    b = await svc.create(author, BuildCreateIn(name="pub", data={}, is_public=True))
    got = await svc.get_public(viewer=None, build_id=b.id)
    assert got.name == "pub"
    assert got.author_pseudo == "A"


async def test_fork_clones_with_lineage(db_session):
    author = await _user(db_session, "a@x.com", "Author")
    forker = await _user(db_session, "f@x.com", "Forker")
    svc = BuildService(db_session)
    src = await svc.create(author, BuildCreateIn(name="Original", data={"v": 1}, is_public=True, tags=["PvP"]))
    fork = await svc.fork(forker, src.id)
    assert fork.user_id == forker.id
    assert fork.forked_from_id == src.id
    assert fork.is_public is False
    assert fork.data == {"v": 1}
    assert fork.tags == ["PvP"]
    assert "copy" in fork.name.lower()


async def test_fork_404_if_private_other(db_session):
    author = await _user(db_session, "a@x.com", "A")
    forker = await _user(db_session, "f@x.com", "F")
    svc = BuildService(db_session)
    src = await svc.create(author, BuildCreateIn(name="secret", data={}, is_public=False))
    with pytest.raises(BuildNotFoundError):
        await svc.fork(forker, src.id)
