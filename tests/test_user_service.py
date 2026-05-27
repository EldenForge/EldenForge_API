import pytest

from core.security import verify_password
from models.user import User
from schemas.auth import RegisterIn
from schemas.user import ChangePasswordIn, UpdatePseudoIn
from services.auth_service import AuthService
from services.user_service import (
    PseudoAlreadyTakenError,
    UserService,
    WrongCurrentPasswordError,
)


class FakeSender:
    def __init__(self):
        self.sent = []
    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def _register(db_session, email="u@x.com", pseudo="User1"):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    return await svc.register_user(RegisterIn(email=email, pseudo=pseudo, password="GoodPass123"))


async def test_update_pseudo_ok(db_session):
    user = await _register(db_session)
    svc = UserService(db_session)
    updated = await svc.update_pseudo(user, UpdatePseudoIn(pseudo="NewPseudo"))
    assert updated.pseudo == "NewPseudo"


async def test_update_pseudo_taken(db_session):
    u1 = await _register(db_session, email="u1@x.com", pseudo="Taken")
    u2 = await _register(db_session, email="u2@x.com", pseudo="Other")
    svc = UserService(db_session)
    with pytest.raises(PseudoAlreadyTakenError):
        await svc.update_pseudo(u2, UpdatePseudoIn(pseudo="Taken"))


async def test_update_pseudo_same_value_idempotent(db_session):
    """If updating to current pseudo, no error."""
    user = await _register(db_session, pseudo="SameOne")
    svc = UserService(db_session)
    updated = await svc.update_pseudo(user, UpdatePseudoIn(pseudo="SameOne"))
    assert updated.pseudo == "SameOne"


async def test_change_password_ok(db_session):
    user = await _register(db_session)
    svc = UserService(db_session)
    await svc.change_password(
        user,
        ChangePasswordIn(current_password="GoodPass123", new_password="BrandNewPass1"),
    )
    await db_session.refresh(user)
    assert verify_password("BrandNewPass1", user.password_hash) is True
    assert verify_password("GoodPass123", user.password_hash) is False


async def test_change_password_wrong_current(db_session):
    user = await _register(db_session)
    svc = UserService(db_session)
    with pytest.raises(WrongCurrentPasswordError):
        await svc.change_password(
            user,
            ChangePasswordIn(current_password="WrongPass1", new_password="BrandNewPass1"),
        )
