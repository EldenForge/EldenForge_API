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


async def test_get_users_me_likes_401_without_auth(client):
    r = await client.get("/users/me/likes")
    assert r.status_code == 401


async def test_get_users_me_likes_returns_only_liked_public(client, db_session):
    from models.build_like import BuildLike
    await _verified_login(client, db_session)
    author_reg = {"email": "author@x.com", "pseudo": "Author", "password": "GoodPass123"}
    await client.post("/auth/register", json=author_reg)
    author = (
        await db_session.execute(select(User).where(User.email == author_reg["email"]))
    ).scalar_one()
    author.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()

    from services.build_service import BuildService
    from schemas.build import BuildCreateIn
    svc = BuildService(db_session)
    b_pub = await svc.create(author, BuildCreateIn(name="pub-liked", data={}, is_public=True))
    b_pub_unliked = await svc.create(author, BuildCreateIn(name="pub-unliked", data={}, is_public=True))
    await db_session.commit()

    me = (await db_session.execute(select(User).where(User.email == REGISTER["email"]))).scalar_one()
    db_session.add(BuildLike(user_id=me.id, build_id=b_pub.id))
    await db_session.commit()

    r = await client.get("/users/me/likes")
    assert r.status_code == 200
    names = {b["name"] for b in r.json()}
    assert names == {"pub-liked"}
    assert all(b["liked_by_me"] for b in r.json())
