import pytest
from sqlalchemy import select

from models.email_token import EmailToken
from models.user import User
from schemas.auth import RegisterIn
from services.auth_service import AuthService, EmailAlreadyExistsError, PseudoAlreadyExistsError


class FakeSender:
    def __init__(self):
        self.sent = []
    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def test_register_creates_user_email_token_and_sends_email(db_session):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    user = await svc.register_user(
        RegisterIn(email="new@example.com", pseudo="NewOne", password="GoodPass123")
    )

    # User created, email not verified
    assert user.email == "new@example.com"
    assert user.email_verified_at is None
    assert user.password_hash.startswith("$argon2id$")

    # Email token of type verification created
    tokens = (
        await db_session.execute(select(EmailToken).where(EmailToken.user_id == user.id))
    ).scalars().all()
    assert len(tokens) == 1
    assert tokens[0].purpose == "email_verification"
    assert tokens[0].used_at is None

    # An email has been "sent"
    assert len(sender.sent) == 1
    assert sender.sent[0]["to"] == "new@example.com"
    assert "verify" in sender.sent[0]["html"].lower()


async def test_register_rejects_duplicate_email_case_insensitive(db_session):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    await svc.register_user(RegisterIn(email="dup@example.com", pseudo="Alpha", password="GoodPass123"))
    with pytest.raises(EmailAlreadyExistsError):
        await svc.register_user(RegisterIn(email="DUP@example.com", pseudo="Beta", password="GoodPass123"))


async def test_register_rejects_duplicate_pseudo_case_insensitive(db_session):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    await svc.register_user(RegisterIn(email="a@x.com", pseudo="Hero", password="GoodPass123"))
    with pytest.raises(PseudoAlreadyExistsError):
        await svc.register_user(RegisterIn(email="b@x.com", pseudo="HERO", password="GoodPass123"))


async def test_register_token_hash_is_not_plaintext(db_session):
    """The raw token sent in the email must not be stored in DB (just its sha256)."""
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    user = await svc.register_user(RegisterIn(email="t@x.com", pseudo="TokTest", password="GoodPass123"))
    token = (
        await db_session.execute(select(EmailToken).where(EmailToken.user_id == user.id))
    ).scalar_one()
    # Stored hash is sha256 hex (64 chars), not raw token
    assert len(token.token_hash) == 64
    # Verify we can recover the hash from the raw sent
    import re
    match = re.search(r"token=([\w-]+)", sender.sent[0]["html"])
    assert match, f"No token=… in email body: {sender.sent[0]['html']}"
    raw = match.group(1)
    from core.security import sha256_hex
    assert sha256_hex(raw) == token.token_hash
