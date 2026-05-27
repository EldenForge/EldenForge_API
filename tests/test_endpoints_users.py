from datetime import datetime, timezone

from sqlalchemy import select

from models.user import User


REGISTER = {"email": "me@x.com", "pseudo": "Original", "password": "GoodPass123"}


async def _verified_login(client, db_session, register_data=REGISTER):
    await client.post("/auth/register", json=register_data)
    user = (
        await db_session.execute(select(User).where(User.email == register_data["email"]))
    ).scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()
    await client.post(
        "/auth/login",
        json={"email": register_data["email"], "password": register_data["password"]},
    )


async def test_get_users_me_200(client, db_session):
    await _verified_login(client, db_session)
    r = await client.get("/users/me")
    assert r.status_code == 200
    assert r.json()["pseudo"] == "Original"


async def test_get_users_me_401(client):
    r = await client.get("/users/me")
    assert r.status_code == 401


async def test_patch_users_me_changes_pseudo(client, db_session):
    await _verified_login(client, db_session)
    r = await client.patch("/users/me", json={"pseudo": "NewName"})
    assert r.status_code == 200
    assert r.json()["pseudo"] == "NewName"

    r2 = await client.get("/users/me")
    assert r2.json()["pseudo"] == "NewName"


async def test_patch_users_me_pseudo_taken_409(client, db_session):
    await _verified_login(client, db_session)
    await client.post("/auth/logout")

    await _verified_login(
        client, db_session,
        {"email": "u2@x.com", "pseudo": "OtherUser", "password": "GoodPass123"},
    )
    r = await client.patch("/users/me", json={"pseudo": "Original"})
    assert r.status_code == 409


async def test_patch_users_me_invalid_pseudo_422(client, db_session):
    await _verified_login(client, db_session)
    r = await client.patch("/users/me", json={"pseudo": "ab"})
    assert r.status_code == 422


async def test_post_change_password_ok(client, db_session):
    await _verified_login(client, db_session)
    r = await client.post(
        "/users/me/password",
        json={"current_password": "GoodPass123", "new_password": "BrandNewPass1"},
    )
    assert r.status_code == 200

    await client.post("/auth/logout")
    r2 = await client.post(
        "/auth/login",
        json={"email": REGISTER["email"], "password": "BrandNewPass1"},
    )
    assert r2.status_code == 200


async def test_post_change_password_wrong_current_401(client, db_session):
    await _verified_login(client, db_session)
    r = await client.post(
        "/users/me/password",
        json={"current_password": "WrongPass1", "new_password": "BrandNewPass1"},
    )
    assert r.status_code == 401


async def test_post_change_password_weak_new_422(client, db_session):
    await _verified_login(client, db_session)
    r = await client.post(
        "/users/me/password",
        json={"current_password": "GoodPass123", "new_password": "weak"},
    )
    assert r.status_code == 422
