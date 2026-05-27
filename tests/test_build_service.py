import uuid

import pytest
from sqlalchemy import select

from models.build import Build
from models.user import User
from schemas.build import BuildCreateIn, BuildUpdateIn
from services.build_service import (
    BuildNotFoundError,
    BuildService,
    NotBuildOwnerError,
)


async def _make_user(session, email="b@x.com", pseudo="Builder"):
    user = User(email=email, pseudo=pseudo, password_hash="$argon2id$h")
    session.add(user)
    await session.flush()
    return user


SAMPLE_DATA = {"stats": {"vigor": 30}, "armor": {"head": "Helm_id"}}


async def test_create_build(db_session):
    user = await _make_user(db_session)
    svc = BuildService(db_session)
    build = await svc.create(user, BuildCreateIn(name="B1", data=SAMPLE_DATA))
    assert build.id is not None
    assert build.user_id == user.id
    assert build.name == "B1"
    assert build.is_public is False


async def test_list_my_builds(db_session):
    u1 = await _make_user(db_session, email="u1@x.com", pseudo="U1")
    u2 = await _make_user(db_session, email="u2@x.com", pseudo="U2")
    svc = BuildService(db_session)
    await svc.create(u1, BuildCreateIn(name="u1-b1", data={}))
    await svc.create(u1, BuildCreateIn(name="u1-b2", data={}))
    await svc.create(u2, BuildCreateIn(name="u2-b1", data={}))

    my_builds = await svc.list_for_user(u1, limit=20, offset=0)
    assert len(my_builds) == 2
    assert {b.name for b in my_builds} == {"u1-b1", "u1-b2"}


async def test_list_pagination(db_session):
    u = await _make_user(db_session)
    svc = BuildService(db_session)
    for i in range(5):
        await svc.create(u, BuildCreateIn(name=f"b{i}", data={}))

    page1 = await svc.list_for_user(u, limit=2, offset=0)
    page2 = await svc.list_for_user(u, limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {b.id for b in page1}.isdisjoint({b.id for b in page2})


async def test_get_my_build(db_session):
    u = await _make_user(db_session)
    svc = BuildService(db_session)
    b = await svc.create(u, BuildCreateIn(name="X", data=SAMPLE_DATA))
    got = await svc.get_for_viewer(u, b.id)
    assert got.id == b.id


async def test_get_other_users_private_build_404(db_session):
    u1 = await _make_user(db_session, email="u1@x.com", pseudo="U1")
    u2 = await _make_user(db_session, email="u2@x.com", pseudo="U2")
    svc = BuildService(db_session)
    b = await svc.create(u1, BuildCreateIn(name="private", data={}, is_public=False))
    with pytest.raises(BuildNotFoundError):
        await svc.get_for_viewer(u2, b.id)


async def test_get_other_users_public_build_ok(db_session):
    u1 = await _make_user(db_session, email="u1@x.com", pseudo="U1")
    u2 = await _make_user(db_session, email="u2@x.com", pseudo="U2")
    svc = BuildService(db_session)
    b = await svc.create(u1, BuildCreateIn(name="public", data={}, is_public=True))
    got = await svc.get_for_viewer(u2, b.id)
    assert got.id == b.id


async def test_get_unknown_id_raises(db_session):
    u = await _make_user(db_session)
    svc = BuildService(db_session)
    with pytest.raises(BuildNotFoundError):
        await svc.get_for_viewer(u, uuid.uuid4())


async def test_update_my_build(db_session):
    u = await _make_user(db_session)
    svc = BuildService(db_session)
    b = await svc.create(u, BuildCreateIn(name="Old", data={"v": 1}))
    updated = await svc.update(u, b.id, BuildUpdateIn(name="New", data={"v": 2}))
    assert updated.name == "New"
    assert updated.data == {"v": 2}


async def test_update_partial(db_session):
    u = await _make_user(db_session)
    svc = BuildService(db_session)
    b = await svc.create(u, BuildCreateIn(name="Original", data={"v": 1}))
    updated = await svc.update(u, b.id, BuildUpdateIn(description="added"))
    assert updated.name == "Original"
    assert updated.description == "added"
    assert updated.data == {"v": 1}


async def test_update_other_users_build_forbidden(db_session):
    u1 = await _make_user(db_session, email="u1@x.com", pseudo="U1")
    u2 = await _make_user(db_session, email="u2@x.com", pseudo="U2")
    svc = BuildService(db_session)
    b = await svc.create(u1, BuildCreateIn(name="Mine", data={}))
    with pytest.raises(NotBuildOwnerError):
        await svc.update(u2, b.id, BuildUpdateIn(name="Hacked"))


async def test_delete_my_build(db_session):
    u = await _make_user(db_session)
    svc = BuildService(db_session)
    b = await svc.create(u, BuildCreateIn(name="ToDelete", data={}))
    await svc.delete(u, b.id)

    rows = (await db_session.execute(select(Build).where(Build.id == b.id))).all()
    assert rows == []


async def test_delete_other_users_build_forbidden(db_session):
    u1 = await _make_user(db_session, email="u1@x.com", pseudo="U1")
    u2 = await _make_user(db_session, email="u2@x.com", pseudo="U2")
    svc = BuildService(db_session)
    b = await svc.create(u1, BuildCreateIn(name="Mine", data={}))
    with pytest.raises(NotBuildOwnerError):
        await svc.delete(u2, b.id)


async def test_delete_unknown_id_raises(db_session):
    u = await _make_user(db_session)
    svc = BuildService(db_session)
    with pytest.raises(BuildNotFoundError):
        await svc.delete(u, uuid.uuid4())
