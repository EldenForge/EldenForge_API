from datetime import datetime, timezone

import pytest

from core.settings import settings
from schemas.auth import LoginIn, RegisterIn
from services.auth_service import (
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
)


class FakeSender:
    def __init__(self):
        self.sent = []
    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def _register_verified(db_session, email="lock@example.com", pseudo="Locker"):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    user = await svc.register_user(RegisterIn(email=email, pseudo=pseudo, password="GoodPass123"))
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()
    return user


async def test_failed_login_increments_counter(db_session):
    user = await _register_verified(db_session)
    svc = AuthService(db_session, FakeSender())
    with pytest.raises(InvalidCredentialsError):
        await svc.login(LoginIn(email=user.email, password="WrongPass1"))
    await db_session.refresh(user)
    assert user.failed_login_count == 1


async def test_lockout_after_max_attempts(db_session):
    user = await _register_verified(db_session, email="x@x.com", pseudo="Maxer")
    svc = AuthService(db_session, FakeSender())
    for _ in range(settings.max_failed_logins):
        with pytest.raises(InvalidCredentialsError):
            await svc.login(LoginIn(email=user.email, password="WrongPass1"))

    await db_session.refresh(user)
    assert user.failed_login_count == settings.max_failed_logins
    assert user.locked_until is not None

    with pytest.raises(AccountLockedError):
        await svc.login(LoginIn(email=user.email, password="GoodPass123"))


async def test_lockout_locked_check_takes_precedence(db_session):
    from datetime import timedelta
    user = await _register_verified(db_session, email="al@x.com", pseudo="AlreadyLocked")
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    await db_session.flush()

    svc = AuthService(db_session, FakeSender())
    with pytest.raises(AccountLockedError):
        await svc.login(LoginIn(email=user.email, password="GoodPass123"))


async def test_successful_login_resets_failed_count(db_session):
    user = await _register_verified(db_session, email="rs@x.com", pseudo="Resetter")
    svc = AuthService(db_session, FakeSender())
    with pytest.raises(InvalidCredentialsError):
        await svc.login(LoginIn(email=user.email, password="WrongPass1"))
    await db_session.refresh(user)
    assert user.failed_login_count == 1

    await svc.login(LoginIn(email=user.email, password="GoodPass123"))
    await db_session.refresh(user)
    assert user.failed_login_count == 0
    assert user.locked_until is None
