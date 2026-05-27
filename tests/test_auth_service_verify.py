from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import generate_url_safe_token, sha256_hex
from models.email_token import EmailToken
from models.user import User
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


async def _register(session, email="v@example.com", pseudo="Verifier"):
    sender = FakeSender()
    svc = AuthService(session, sender)
    user = await svc.register_user(RegisterIn(email=email, pseudo=pseudo, password="GoodPass123"))
    return user, sender


async def test_verify_email_marks_user_verified(db_session):
    user, sender = await _register(db_session)
    assert user.email_verified_at is None

    import re
    raw = re.search(r"token=([\w-]+)", sender.sent[0]["html"]).group(1)

    svc = AuthService(db_session, FakeSender())
    await svc.verify_email(raw)
    await db_session.refresh(user)

    assert user.email_verified_at is not None


async def test_verify_email_marks_token_used(db_session):
    user, sender = await _register(db_session)
    import re
    raw = re.search(r"token=([\w-]+)", sender.sent[0]["html"]).group(1)

    svc = AuthService(db_session, FakeSender())
    await svc.verify_email(raw)

    token = (
        await db_session.execute(select(EmailToken).where(EmailToken.user_id == user.id))
    ).scalar_one()
    assert token.used_at is not None


async def test_verify_email_unknown_token(db_session):
    svc = AuthService(db_session, FakeSender())
    with pytest.raises(ServiceInvalidTokenError):
        await svc.verify_email("totally-unknown-raw-token")


async def test_verify_email_expired_token(db_session):
    user, sender = await _register(db_session)
    import re
    raw = re.search(r"token=([\w-]+)", sender.sent[0]["html"]).group(1)

    token = (
        await db_session.execute(select(EmailToken).where(EmailToken.user_id == user.id))
    ).scalar_one()
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    svc = AuthService(db_session, FakeSender())
    with pytest.raises(TokenExpiredError):
        await svc.verify_email(raw)


async def test_verify_email_token_already_used(db_session):
    user, sender = await _register(db_session)
    import re
    raw = re.search(r"token=([\w-]+)", sender.sent[0]["html"]).group(1)

    svc = AuthService(db_session, FakeSender())
    await svc.verify_email(raw)

    with pytest.raises(TokenAlreadyUsedError):
        await svc.verify_email(raw)


async def test_verify_email_rejects_password_reset_purpose(db_session):
    """A password_reset token must not be usable to activate an account."""
    user, _ = await _register(db_session)
    raw = generate_url_safe_token(32)
    token = EmailToken(
        user_id=user.id,
        token_hash=sha256_hex(raw),
        purpose="password_reset",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(token)
    await db_session.flush()

    svc = AuthService(db_session, FakeSender())
    with pytest.raises(ServiceInvalidTokenError):
        await svc.verify_email(raw)
