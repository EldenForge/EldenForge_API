from datetime import datetime, timezone

from sqlalchemy import select

from models.refresh_token import RefreshToken
from models.user import User


REGISTER = {"email": "pr2c@example.com", "pseudo": "Pr2cUser", "password": "GoodPass123"}


async def _login(client, db_session):
    """Helper : register, verify email, login. Returns the login response."""
    await client.post("/auth/register", json=REGISTER)
    user = (
        await db_session.execute(select(User).where(User.email == REGISTER["email"]))
    ).scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()
    return await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )


async def test_refresh_200_rotates_tokens(client, db_session):
    await _login(client, db_session)
    old_refresh = client.cookies.get("refresh_token")
    assert old_refresh

    r = await client.post("/auth/refresh")
    assert r.status_code == 200, r.text
    assert client.cookies.get("refresh_token") != old_refresh
    assert client.cookies.get("access_token") is not None


async def test_refresh_401_no_cookie(client):
    r = await client.post("/auth/refresh")
    assert r.status_code == 401


async def test_refresh_401_invalid_token(client):
    client.cookies.set("refresh_token", "totally-invalid-raw")
    r = await client.post("/auth/refresh")
    assert r.status_code == 401


async def test_logout_204_revokes_in_db(client, db_session):
    await _login(client, db_session)
    raw = client.cookies.get("refresh_token")

    r = await client.post("/auth/logout")
    assert r.status_code == 204

    from core.security import sha256_hex
    row = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(raw))
        )
    ).scalar_one()
    assert row.revoked_at is not None


async def test_logout_204_silent_without_cookie(client):
    r = await client.post("/auth/logout")
    assert r.status_code == 204


async def test_login_423_account_locked(client, db_session):
    await client.post("/auth/register", json=REGISTER)
    user = (
        await db_session.execute(select(User).where(User.email == REGISTER["email"]))
    ).scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    from core.settings import settings
    for _ in range(settings.max_failed_logins):
        await client.post(
            "/auth/login",
            json={"email": REGISTER["email"], "password": "WrongPass1"},
        )
    r = await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert r.status_code == 423
