import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.user import User


async def _make_user(session, **overrides):
    defaults = dict(
        email="player1@example.com",
        pseudo="Tarnished",
        password_hash="$argon2id$dummyhash",
    )
    defaults.update(overrides)
    user = User(**defaults)
    session.add(user)
    await session.flush()
    return user


async def test_create_user_ok(db_session):
    user = await _make_user(db_session)
    assert isinstance(user.id, uuid.UUID)
    assert user.failed_login_count == 0
    assert user.email_verified_at is None
    assert isinstance(user.created_at, datetime)
    assert user.created_at.tzinfo is not None  # timezone-aware
    assert user.updated_at is not None


async def test_email_unique_case_insensitive(db_session):
    await _make_user(db_session, email="Foo@example.com", pseudo="A")
    with pytest.raises(IntegrityError):
        await _make_user(db_session, email="foo@EXAMPLE.com", pseudo="B")


async def test_pseudo_unique_case_insensitive(db_session):
    await _make_user(db_session, email="a@x.com", pseudo="Hero")
    with pytest.raises(IntegrityError):
        await _make_user(db_session, email="b@x.com", pseudo="HERO")


async def test_user_round_trip(db_session):
    user = await _make_user(db_session, email="round@trip.com", pseudo="Round")
    fetched = (
        await db_session.execute(select(User).where(User.email == "round@trip.com"))
    ).scalar_one()
    assert fetched.id == user.id
    assert fetched.pseudo == "Round"
