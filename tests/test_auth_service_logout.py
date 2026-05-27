from datetime import datetime, timezone

from sqlalchemy import select

from core.security import sha256_hex
from models.refresh_token import RefreshToken
from schemas.auth import LoginIn, RegisterIn
from services.auth_service import AuthService


class FakeSender:
    def __init__(self):
        self.sent = []

    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def _login(db_session):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    user = await svc.register_user(RegisterIn(email="out@example.com", pseudo="LoggerOut", password="GoodPass123"))
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()
    result = await svc.login(LoginIn(email="out@example.com", password="GoodPass123"))
    return user, result.refresh_token


async def test_logout_revokes_refresh_token(db_session):
    user, raw = await _login(db_session)
    svc = AuthService(db_session, FakeSender())
    await svc.logout(raw)

    row = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(raw))
        )
    ).scalar_one()
    assert row.revoked_at is not None


async def test_logout_silent_if_unknown_token(db_session):
    svc = AuthService(db_session, FakeSender())
    await svc.logout("unknown-raw")  # no exception


async def test_logout_silent_if_no_token(db_session):
    svc = AuthService(db_session, FakeSender())
    await svc.logout(None)


async def test_logout_idempotent(db_session):
    user, raw = await _login(db_session)
    svc = AuthService(db_session, FakeSender())
    await svc.logout(raw)
    await svc.logout(raw)  # already revoked, no exception
