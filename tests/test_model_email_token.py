from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from models.email_token import EmailToken
from models.user import User


async def _make_user(session, email="t@example.com", pseudo="Tok"):
    user = User(email=email, pseudo=pseudo, password_hash="$argon2id$h")
    session.add(user)
    await session.flush()
    return user


async def test_create_email_verification_token(db_session):
    user = await _make_user(db_session)
    token = EmailToken(
        user_id=user.id,
        token_hash="a" * 64,
        purpose="email_verification",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(token)
    await db_session.flush()
    assert token.id is not None
    assert token.used_at is None


async def test_create_password_reset_token(db_session):
    user = await _make_user(db_session, email="r@x.com", pseudo="Reset")
    token = EmailToken(
        user_id=user.id,
        token_hash="b" * 64,
        purpose="password_reset",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(token)
    await db_session.flush()
    assert token.purpose == "password_reset"


async def test_email_token_purpose_check(db_session):
    user = await _make_user(db_session, email="bad@x.com", pseudo="Bad")
    token = EmailToken(
        user_id=user.id,
        token_hash="c" * 64,
        purpose="bogus_purpose",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(token)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_email_token_hash_unique(db_session):
    user = await _make_user(db_session, email="u1@x.com", pseudo="U1")
    other = await _make_user(db_session, email="u2@x.com", pseudo="U2")
    shared = "d" * 64
    t1 = EmailToken(
        user_id=user.id,
        token_hash=shared,
        purpose="email_verification",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(t1)
    await db_session.flush()

    t2 = EmailToken(
        user_id=other.id,
        token_hash=shared,
        purpose="password_reset",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(t2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
