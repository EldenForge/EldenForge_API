from datetime import datetime, timezone

from sqlalchemy import select

from models.user import User


REGISTER = {"email": "alice@example.com", "pseudo": "Alice", "password": "GoodPass123"}


async def test_register_201(client, email_sink, db_session):
    r = await client.post("/auth/register", json=REGISTER)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["pseudo"] == "Alice"
    assert body["email_verified_at"] is None

    # Un email a été envoyé
    assert len(email_sink.sent) == 1
    assert email_sink.sent[0]["to"] == "alice@example.com"


async def test_register_409_email_duplicate(client):
    await client.post("/auth/register", json=REGISTER)
    r = await client.post(
        "/auth/register",
        json={**REGISTER, "pseudo": "OtherPseudo"},
    )
    assert r.status_code == 409


async def test_register_409_pseudo_duplicate(client):
    await client.post("/auth/register", json=REGISTER)
    r = await client.post(
        "/auth/register",
        json={**REGISTER, "email": "other@x.com"},
    )
    assert r.status_code == 409


async def test_register_422_weak_password(client):
    r = await client.post(
        "/auth/register",
        json={**REGISTER, "password": "weak"},
    )
    assert r.status_code == 422


async def test_login_403_email_not_verified(client):
    await client.post("/auth/register", json=REGISTER)
    r = await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert r.status_code == 403


async def test_login_200_sets_cookies(client, db_session):
    await client.post("/auth/register", json=REGISTER)

    # Mark email as verified
    user = (
        await db_session.execute(select(User).where(User.email == REGISTER["email"]))
    ).scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    r = await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies


async def test_login_401_wrong_password(client, db_session):
    await client.post("/auth/register", json=REGISTER)
    user = (
        await db_session.execute(select(User).where(User.email == REGISTER["email"]))
    ).scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    r = await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": "WrongPass123"},
    )
    assert r.status_code == 401


async def test_me_401_without_cookie(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_200_with_valid_cookie(client, db_session):
    # Register + verify + login to get cookies
    await client.post("/auth/register", json=REGISTER)
    user = (
        await db_session.execute(select(User).where(User.email == REGISTER["email"]))
    ).scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    login_resp = await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert login_resp.status_code == 200

    # /auth/me uses cookies already posted on AsyncClient
    r = await client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == REGISTER["email"]
