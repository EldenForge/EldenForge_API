from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import generate_url_safe_token, sha256_hex, verify_password
from models.email_token import EmailToken
from schemas.auth import RegisterIn
from services.auth_service import (
    AuthService,
    InvalidTokenError as ServiceInvalidTokenError,
    TokenAlreadyUsedError,
    TokenExpiredError,
)


class FakeSender:
    def __init__(self):
        self.sent = []
    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def _register_and_get_reset_token(session, email="r@example.com", pseudo="Reseter"):
    sender = FakeSender()
    svc = AuthService(session, sender)
    user = await svc.register_user(RegisterIn(email=email, pseudo=pseudo, password="GoodPass123"))
    sender.sent.clear()
    await svc.request_password_reset(email)
    import re
    raw = re.search(r"token=([\w-]+)", sender.sent[0]["html"]).group(1)
    return user, raw


async def test_reset_password_updates_hash(db_session):
    user, raw = await _register_and_get_reset_token(db_session)
    old_hash = user.password_hash

    svc = AuthService(db_session, FakeSender())
    await svc.reset_password(raw, "BrandNewPass1")
    await db_session.refresh(user)

    assert user.password_hash != old_hash
    assert verify_password("BrandNewPass1", user.password_hash) is True
    assert verify_password("GoodPass123", user.password_hash) is False


async def test_reset_password_marks_token_used(db_session):
    user, raw = await _register_and_get_reset_token(db_session)

    svc = AuthService(db_session, FakeSender())
    await svc.reset_password(raw, "BrandNewPass1")

    token = (
        await db_session.execute(
            select(EmailToken).where(
                EmailToken.user_id == user.id,
                EmailToken.purpose == "password_reset",
            )
        )
    ).scalar_one()
    assert token.used_at is not None


async def test_reset_password_unknown_token(db_session):
    svc = AuthService(db_session, FakeSender())
    with pytest.raises(ServiceInvalidTokenError):
        await svc.reset_password("unknown", "BrandNewPass1")


async def test_reset_password_expired(db_session):
    user, raw = await _register_and_get_reset_token(db_session, email="exp@x.com", pseudo="Expired")
    token = (
        await db_session.execute(
            select(EmailToken).where(
                EmailToken.user_id == user.id,
                EmailToken.purpose == "password_reset",
            )
        )
    ).scalar_one()
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    svc = AuthService(db_session, FakeSender())
    with pytest.raises(TokenExpiredError):
        await svc.reset_password(raw, "BrandNewPass1")


async def test_reset_password_already_used(db_session):
    user, raw = await _register_and_get_reset_token(db_session, email="used@x.com", pseudo="Used")
    svc = AuthService(db_session, FakeSender())
    await svc.reset_password(raw, "BrandNewPass1")
    with pytest.raises(TokenAlreadyUsedError):
        await svc.reset_password(raw, "AnotherPass1")


async def test_reset_password_rejects_verification_purpose(db_session):
    """A purpose=email_verification token must not be usable to reset a password."""
    user, _ = await _register_and_get_reset_token(db_session, email="cross@x.com", pseudo="Cross")
    raw = generate_url_safe_token(32)
    bad = EmailToken(
        user_id=user.id,
        token_hash=sha256_hex(raw),
        purpose="email_verification",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(bad)
    await db_session.flush()

    svc = AuthService(db_session, FakeSender())
    with pytest.raises(ServiceInvalidTokenError):
        await svc.reset_password(raw, "BrandNewPass1")
