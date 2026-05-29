import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.build import Build
from models.build_like import BuildLike
from models.user import User


async def _user(session, email="pb@x.com", pseudo="Pub"):
    u = User(email=email, pseudo=pseudo, password_hash="$argon2id$h")
    session.add(u)
    await session.flush()
    return u


async def test_build_has_tags_likecount_forkedfrom_defaults(db_session):
    u = await _user(db_session)
    b = Build(user_id=u.id, name="B", data={})
    db_session.add(b)
    await db_session.flush()
    assert b.tags == []
    assert b.like_count == 0
    assert b.forked_from_id is None


async def test_build_tags_roundtrip(db_session):
    u = await _user(db_session)
    b = Build(user_id=u.id, name="B", data={}, tags=["Strength", "PvP"])
    db_session.add(b)
    await db_session.flush()
    fetched = (await db_session.execute(select(Build).where(Build.id == b.id))).scalar_one()
    assert fetched.tags == ["Strength", "PvP"]


async def test_build_forked_from_self_reference(db_session):
    u = await _user(db_session)
    src = Build(user_id=u.id, name="Source", data={})
    db_session.add(src)
    await db_session.flush()
    fork = Build(user_id=u.id, name="Source (copy)", data={}, forked_from_id=src.id)
    db_session.add(fork)
    await db_session.flush()
    assert fork.forked_from_id == src.id


async def test_build_like_unique_per_user_build(db_session):
    u = await _user(db_session)
    b = Build(user_id=u.id, name="B", data={})
    db_session.add(b)
    await db_session.flush()
    db_session.add(BuildLike(user_id=u.id, build_id=b.id))
    await db_session.flush()
    db_session.add(BuildLike(user_id=u.id, build_id=b.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_build_like_cascade_on_build_delete(db_session):
    from sqlalchemy import delete
    u = await _user(db_session)
    b = Build(user_id=u.id, name="B", data={})
    db_session.add(b)
    await db_session.flush()
    db_session.add(BuildLike(user_id=u.id, build_id=b.id))
    await db_session.flush()
    await db_session.execute(delete(Build).where(Build.id == b.id))
    await db_session.flush()
    rows = (await db_session.execute(select(BuildLike).where(BuildLike.build_id == b.id))).all()
    assert rows == []
