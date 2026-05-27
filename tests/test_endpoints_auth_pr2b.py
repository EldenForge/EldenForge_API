import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from models.email_token import EmailToken
from models.user import User


REGISTER = {"email": "pr2b@example.com", "pseudo": "Pr2bUser", "password": "GoodPass123"}


def _extract_token(html: str) -> str:
    match = re.search(r"token=([\w-]+)", html)
    assert match, f"No token in HTML: {html}"
    return match.group(1)


async def test_verify_200_marks_user_verified(client, email_sink, db_session):
    await client.post("/auth/register", json=REGISTER)
    raw = _extract_token(email_sink.sent[0]["html"])

    r = await client.get(f"/auth/verify?token={raw}")
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    user = (
        await db_session.execute(select(User).where(User.email == REGISTER["email"]))
    ).scalar_one()
    assert user.email_verified_at is not None


async def test_verify_404_unknown_token(client):
    r = await client.get("/auth/verify?token=totally-unknown")
    assert r.status_code == 404


async def test_verify_410_already_used(client, email_sink):
    await client.post("/auth/register", json=REGISTER)
    raw = _extract_token(email_sink.sent[0]["html"])
    await client.get(f"/auth/verify?token={raw}")  # 1st time → 200
    r = await client.get(f"/auth/verify?token={raw}")
    assert r.status_code == 410


async def test_verify_410_expired(client, email_sink, db_session):
    await client.post("/auth/register", json=REGISTER)
    raw = _extract_token(email_sink.sent[0]["html"])

    token = (
        await db_session.execute(select(EmailToken))
    ).scalar_one()
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    r = await client.get(f"/auth/verify?token={raw}")
    assert r.status_code == 410


async def test_forgot_202_user_exists_sends_email(client, email_sink):
    await client.post("/auth/register", json=REGISTER)
    email_sink.sent.clear()

    r = await client.post("/auth/forgot", json={"email": REGISTER["email"]})
    assert r.status_code == 202
    assert len(email_sink.sent) == 1
    assert "reset" in email_sink.sent[0]["html"].lower()


async def test_forgot_202_user_unknown_no_email(client, email_sink):
    r = await client.post("/auth/forgot", json={"email": "nobody@x.com"})
    assert r.status_code == 202
    assert email_sink.sent == []


async def test_reset_200_changes_password(client, email_sink, db_session):
    await client.post("/auth/register", json=REGISTER)
    user = (
        await db_session.execute(select(User).where(User.email == REGISTER["email"]))
    ).scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()
    email_sink.sent.clear()

    await client.post("/auth/forgot", json={"email": REGISTER["email"]})
    raw = _extract_token(email_sink.sent[0]["html"])

    r = await client.post("/auth/reset", json={"token": raw, "new_password": "NewPass987"})
    assert r.status_code == 200, r.text

    # Login with new password works
    login = await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": "NewPass987"},
    )
    assert login.status_code == 200


async def test_reset_404_unknown_token(client):
    r = await client.post(
        "/auth/reset",
        json={"token": "totally-unknown", "new_password": "BrandNewPass1"},
    )
    assert r.status_code == 404


async def test_reset_422_weak_password(client, email_sink):
    await client.post("/auth/register", json=REGISTER)
    email_sink.sent.clear()
    await client.post("/auth/forgot", json={"email": REGISTER["email"]})
    raw = _extract_token(email_sink.sent[0]["html"])

    r = await client.post(
        "/auth/reset",
        json={"token": raw, "new_password": "weak"},
    )
    assert r.status_code == 422
