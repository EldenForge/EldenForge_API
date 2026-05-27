import pytest

from models.user import User
from schemas.auth import LoginIn, RegisterIn
from services.auth_service import (
    AuthService,
    EmailNotVerifiedError,
    InvalidCredentialsError,
)


class FakeSender:
    def __init__(self):
        self.sent = []
    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def _register(session, **overrides):
    sender = FakeSender()
    svc = AuthService(session, sender)
    data = dict(email="u@example.com", pseudo="LoginU", password="GoodPass123")
    data.update(overrides)
    return await svc.register_user(RegisterIn(**data))


async def test_login_rejects_unverified_email(db_session):
    await _register(db_session)
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    with pytest.raises(EmailNotVerifiedError):
        await svc.login(LoginIn(email="u@example.com", password="GoodPass123"))


async def test_login_succeeds_after_email_verified(db_session):
    user = await _register(db_session)
    from datetime import datetime, timezone
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    sender = FakeSender()
    svc = AuthService(db_session, sender)
    result = await svc.login(LoginIn(email="u@example.com", password="GoodPass123"))

    assert result.user.id == user.id
    assert isinstance(result.access_token, str) and len(result.access_token) > 20
    assert isinstance(result.refresh_token, str) and len(result.refresh_token) > 40


async def test_login_wrong_password(db_session):
    user = await _register(db_session)
    from datetime import datetime, timezone
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    sender = FakeSender()
    svc = AuthService(db_session, sender)
    with pytest.raises(InvalidCredentialsError):
        await svc.login(LoginIn(email="u@example.com", password="WrongPass123"))


async def test_login_unknown_email(db_session):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    with pytest.raises(InvalidCredentialsError):
        await svc.login(LoginIn(email="unknown@x.com", password="WhateverPass1"))


async def test_login_creates_refresh_token_row(db_session):
    user = await _register(db_session)
    from datetime import datetime, timezone
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    sender = FakeSender()
    svc = AuthService(db_session, sender)
    result = await svc.login(LoginIn(email="u@example.com", password="GoodPass123"))

    from sqlalchemy import select
    from models.refresh_token import RefreshToken
    rows = (await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))).scalars().all()
    assert len(rows) == 1
    # The stored hash matches the raw returned
    from core.security import sha256_hex
    assert rows[0].token_hash == sha256_hex(result.refresh_token)
