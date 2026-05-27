from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from models.refresh_token import RefreshToken
from models.user import User


async def _make_user(session, email="rt@example.com", pseudo="Rt"):
    user = User(email=email, pseudo=pseudo, password_hash="$argon2id$h")
    session.add(user)
    await session.flush()
    return user


async def test_create_refresh_token(db_session):
    user = await _make_user(db_session)
    token = RefreshToken(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        user_agent="Mozilla/5.0",
        ip="192.168.1.1",
    )
    db_session.add(token)
    await db_session.flush()
    assert token.id is not None
    assert token.revoked_at is None


async def test_refresh_token_hash_unique(db_session):
    user = await _make_user(db_session, email="u1@x.com", pseudo="U1")
    shared = "b" * 64
    t1 = RefreshToken(
        user_id=user.id,
        token_hash=shared,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(t1)
    await db_session.flush()

    t2 = RefreshToken(
        user_id=user.id,
        token_hash=shared,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(t2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_refresh_token_optional_audit_fields(db_session):
    """user_agent et ip sont nullable."""
    user = await _make_user(db_session, email="opt@x.com", pseudo="Opt")
    token = RefreshToken(
        user_id=user.id,
        token_hash="c" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(token)
    await db_session.flush()
    assert token.user_agent is None
    assert token.ip is None
