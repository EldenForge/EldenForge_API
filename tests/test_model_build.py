import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.build import Build
from models.user import User


async def _make_user(session, email="b@example.com", pseudo="Builder"):
    user = User(email=email, pseudo=pseudo, password_hash="$argon2id$h")
    session.add(user)
    await session.flush()
    return user


SAMPLE_BUILD_DATA = {
    "stats": {
        "vigor": 30,
        "mind": 12,
        "endurance": 20,
        "strength": 40,
        "dexterity": 14,
        "intelligence": 9,
        "faith": 9,
        "arcane": 7,
    },
    "armor": {"head": "Helm_id", "chest": None, "hands": None, "legs": None},
    "talismans": [None, None, None, None],
    "weapons": {"right": "Sword_id", "left": None},
    "spells": [None] * 10,
    "spirit": None,
    "guide": "Hit the boss [Margit]",
}


async def test_create_build_ok(db_session):
    user = await _make_user(db_session)
    build = Build(user_id=user.id, name="My first build", data=SAMPLE_BUILD_DATA)
    db_session.add(build)
    await db_session.flush()
    assert build.id is not None
    assert build.is_public is False
    assert build.description is None


async def test_build_requires_user(db_session):
    build = Build(user_id=None, name="Orphan", data={})  # type: ignore[arg-type]
    db_session.add(build)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_build_name_must_be_non_empty(db_session):
    user = await _make_user(db_session, email="c@x.com", pseudo="Empty")
    build = Build(user_id=user.id, name="", data={})
    db_session.add(build)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_build_name_max_100(db_session):
    user = await _make_user(db_session, email="d@x.com", pseudo="Long")
    build = Build(user_id=user.id, name="x" * 101, data={})
    db_session.add(build)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_build_description_max_2000(db_session):
    user = await _make_user(db_session, email="e@x.com", pseudo="Desc")
    build = Build(
        user_id=user.id,
        name="Valid",
        description="x" * 2001,
        data={},
    )
    db_session.add(build)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_jsonb_roundtrip(db_session):
    user = await _make_user(db_session, email="j@x.com", pseudo="Json")
    build = Build(user_id=user.id, name="JSON test", data=SAMPLE_BUILD_DATA)
    db_session.add(build)
    await db_session.flush()
    build_id = build.id

    fetched = (
        await db_session.execute(select(Build).where(Build.id == build_id))
    ).scalar_one()
    assert fetched.data == SAMPLE_BUILD_DATA
    assert fetched.data["stats"]["vigor"] == 30
    assert fetched.data["guide"] == "Hit the boss [Margit]"
