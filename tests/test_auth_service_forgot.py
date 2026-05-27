from sqlalchemy import select

from models.email_token import EmailToken
from schemas.auth import RegisterIn
from services.auth_service import AuthService


class FakeSender:
    def __init__(self):
        self.sent = []
    async def send(self, to, subject, html_body):
        self.sent.append({"to": to, "subject": subject, "html": html_body})


async def test_request_password_reset_sends_email_if_user_exists(db_session):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    await svc.register_user(RegisterIn(email="forgot@x.com", pseudo="Forgot", password="GoodPass123"))
    sender.sent.clear()  # ignore the verification email

    await svc.request_password_reset("forgot@x.com")

    assert len(sender.sent) == 1
    assert sender.sent[0]["to"] == "forgot@x.com"
    assert "reset" in sender.sent[0]["html"].lower()


async def test_request_password_reset_silent_if_user_unknown(db_session):
    """Anti user enumeration : no error, no email."""
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    await svc.request_password_reset("nobody@x.com")
    assert sender.sent == []


async def test_request_password_reset_creates_token_row(db_session):
    sender = FakeSender()
    svc = AuthService(db_session, sender)
    user = await svc.register_user(RegisterIn(email="r@x.com", pseudo="Rst", password="GoodPass123"))

    await svc.request_password_reset("r@x.com")

    tokens = (
        await db_session.execute(
            select(EmailToken).where(
                EmailToken.user_id == user.id,
                EmailToken.purpose == "password_reset",
            )
        )
    ).scalars().all()
    assert len(tokens) == 1
    assert tokens[0].used_at is None
