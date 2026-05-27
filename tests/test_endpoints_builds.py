from datetime import datetime, timezone

from sqlalchemy import select

from models.user import User


REGISTER = {"email": "owner@x.com", "pseudo": "Owner", "password": "GoodPass123"}
REGISTER_OTHER = {"email": "other@x.com", "pseudo": "OtherU", "password": "GoodPass123"}


async def _verified_login(client, db_session, register_data):
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


SAMPLE_DATA = {"stats": {"vigor": 30}, "armor": {"head": "h"}}


async def test_create_build_201(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    r = await client.post(
        "/builds",
        json={"name": "My Build", "data": SAMPLE_DATA},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "My Build"
    assert body["data"] == SAMPLE_DATA
    assert body["is_public"] is False


async def test_create_build_401_without_auth(client):
    r = await client.post("/builds", json={"name": "X", "data": {}})
    assert r.status_code == 401


async def test_create_build_422_no_name(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    r = await client.post("/builds", json={"data": SAMPLE_DATA})
    assert r.status_code == 422


async def test_list_my_builds(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    for i in range(3):
        await client.post("/builds", json={"name": f"b{i}", "data": {}})

    r = await client.get("/builds")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3
    assert {b["name"] for b in items} == {"b0", "b1", "b2"}


async def test_list_pagination_limit_offset(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    for i in range(5):
        await client.post("/builds", json={"name": f"b{i}", "data": {}})

    r1 = await client.get("/builds?limit=2&offset=0")
    r2 = await client.get("/builds?limit=2&offset=2")
    assert len(r1.json()) == 2
    assert len(r2.json()) == 2
    ids1 = {b["id"] for b in r1.json()}
    ids2 = {b["id"] for b in r2.json()}
    assert ids1.isdisjoint(ids2)


async def test_get_my_build(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    created = await client.post("/builds", json={"name": "Get me", "data": SAMPLE_DATA})
    build_id = created.json()["id"]

    r = await client.get(f"/builds/{build_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Get me"
    assert r.json()["data"] == SAMPLE_DATA


async def test_get_other_users_private_build_404(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    created = await client.post("/builds", json={"name": "Secret", "data": {}, "is_public": False})
    build_id = created.json()["id"]

    await client.post("/auth/logout")
    await _verified_login(client, db_session, REGISTER_OTHER)
    r = await client.get(f"/builds/{build_id}")
    assert r.status_code == 404


async def test_get_other_users_public_build_200(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    created = await client.post("/builds", json={"name": "Public", "data": {}, "is_public": True})
    build_id = created.json()["id"]

    await client.post("/auth/logout")
    await _verified_login(client, db_session, REGISTER_OTHER)
    r = await client.get(f"/builds/{build_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Public"


async def test_update_my_build(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    created = await client.post("/builds", json={"name": "Old", "data": {"v": 1}})
    build_id = created.json()["id"]

    r = await client.put(f"/builds/{build_id}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"
    assert r.json()["data"] == {"v": 1}


async def test_update_other_users_build_403(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    created = await client.post("/builds", json={"name": "Mine", "data": {}})
    build_id = created.json()["id"]

    await client.post("/auth/logout")
    await _verified_login(client, db_session, REGISTER_OTHER)
    r = await client.put(f"/builds/{build_id}", json={"name": "Hacked"})
    assert r.status_code == 403


async def test_delete_my_build(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    created = await client.post("/builds", json={"name": "Bye", "data": {}})
    build_id = created.json()["id"]

    r = await client.delete(f"/builds/{build_id}")
    assert r.status_code == 204

    r = await client.get(f"/builds/{build_id}")
    assert r.status_code == 404


async def test_delete_other_users_build_403(client, db_session):
    await _verified_login(client, db_session, REGISTER)
    created = await client.post("/builds", json={"name": "Mine", "data": {}})
    build_id = created.json()["id"]

    await client.post("/auth/logout")
    await _verified_login(client, db_session, REGISTER_OTHER)
    r = await client.delete(f"/builds/{build_id}")
    assert r.status_code == 403
