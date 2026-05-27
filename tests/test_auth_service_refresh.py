from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import sha256_hex
from models.refresh_token import RefreshToken
from models.user import User
from schemas.auth import LoginIn, RegisterIn
from services.auth_service import (
    AuthService,
    InvalidRefreshTokenError,
)


class FakeSender:
    def __init__(self):
        self.sent = []
    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def _login(db_session, email="ref@example.com", pseudo="Refresher"):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    user = await svc.register_user(RegisterIn(email=email, pseudo=pseudo, password="GoodPass123"))
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()
    result = await svc.login(LoginIn(email=email, password="GoodPass123"))
    return user, result.refresh_token


async def test_refresh_returns_new_tokens(db_session):
    user, old_raw = await _login(db_session)
    svc = AuthService(db_session, FakeSender())
    result = await svc.refresh(old_raw)
    assert isinstance(result.access_token, str) and len(result.access_token) > 20
    assert isinstance(result.refresh_token, str) and len(result.refresh_token) > 40
    assert result.refresh_token != old_raw


async def test_refresh_revokes_old_token(db_session):
    user, old_raw = await _login(db_session)
    old_hash = sha256_hex(old_raw)

    svc = AuthService(db_session, FakeSender())
    await svc.refresh(old_raw)

    old_row = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == old_hash)
        )
    ).scalar_one()
    assert old_row.revoked_at is not None


async def test_refresh_creates_new_row(db_session):
    user, old_raw = await _login(db_session, email="r2@x.com", pseudo="Newrow")
    svc = AuthService(db_session, FakeSender())
    result = await svc.refresh(old_raw)

    new_row = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(result.refresh_token))
        )
    ).scalar_one()
    assert new_row.user_id == user.id
    assert new_row.revoked_at is None


async def test_refresh_unknown_token(db_session):
    svc = AuthService(db_session, FakeSender())
    with pytest.raises(InvalidRefreshTokenError):
        await svc.refresh("totally-unknown-raw")


async def test_refresh_revoked_token(db_session):
    user, old_raw = await _login(db_session, email="rev@x.com", pseudo="Revoked")
    svc = AuthService(db_session, FakeSender())
    await svc.refresh(old_raw)
    with pytest.raises(InvalidRefreshTokenError):
        await svc.refresh(old_raw)


async def test_refresh_expired_token(db_session):
    user, old_raw = await _login(db_session, email="exp@x.com", pseudo="Expired")
    row = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(old_raw))
        )
    ).scalar_one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    svc = AuthService(db_session, FakeSender())
    with pytest.raises(InvalidRefreshTokenError):
        await svc.refresh(old_raw)
