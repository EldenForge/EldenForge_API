from datetime import datetime, timezone

from sqlalchemy import select

from models.user import User


REG = {"email": "owner@x.com", "pseudo": "Owner", "password": "GoodPass123"}
REG2 = {"email": "forker@x.com", "pseudo": "Forker", "password": "GoodPass123"}


async def _verified_login(client, db_session, reg):
    await client.post("/auth/register", json=reg)
    u = (await db_session.execute(select(User).where(User.email == reg["email"]))).scalar_one()
    u.email_verified_at = datetime.now(timezone.utc)
    await db_session.flush()
    await client.post("/auth/login", json={"email": reg["email"], "password": reg["password"]})


async def test_public_list_empty_anon(client):
    r = await client.get("/public/builds")
    assert r.status_code == 200
    assert r.json() == []


async def test_public_list_shows_public_only(client, db_session):
    await _verified_login(client, db_session, REG)
    await client.post("/builds", json={"name": "pub", "data": {}, "is_public": True})
    await client.post("/builds", json={"name": "priv", "data": {}, "is_public": False})
    await client.post("/auth/logout")
    r = await client.get("/public/builds")
    names = {b["name"] for b in r.json()}
    assert "pub" in names and "priv" not in names


async def test_public_list_filter_tags(client, db_session):
    await _verified_login(client, db_session, REG)
    await client.post("/builds", json={"name": "str", "data": {}, "is_public": True, "tags": ["Strength"]})
    await client.post("/builds", json={"name": "mage", "data": {}, "is_public": True, "tags": ["Intelligence"]})
    r = await client.get("/public/builds?tags=Strength")
    assert {b["name"] for b in r.json()} == {"str"}


async def test_public_detail_ok(client, db_session):
    await _verified_login(client, db_session, REG)
    created = await client.post("/builds", json={"name": "pub", "data": {"v": 1}, "is_public": True})
    bid = created.json()["id"]
    r = await client.get(f"/public/builds/{bid}")
    assert r.status_code == 200
    assert r.json()["author_pseudo"] == "Owner"
    assert r.json()["data"] == {"v": 1}


async def test_public_detail_404_private_other(client, db_session):
    await _verified_login(client, db_session, REG)
    created = await client.post("/builds", json={"name": "secret", "data": {}, "is_public": False})
    bid = created.json()["id"]
    await client.post("/auth/logout")
    await _verified_login(client, db_session, REG2)
    r = await client.get(f"/public/builds/{bid}")
    assert r.status_code == 404


async def test_fork_creates_copy_with_lineage(client, db_session):
    await _verified_login(client, db_session, REG)
    created = await client.post("/builds", json={"name": "Original", "data": {"v": 1}, "is_public": True, "tags": ["PvP"]})
    bid = created.json()["id"]
    await client.post("/auth/logout")
    await _verified_login(client, db_session, REG2)
    r = await client.post(f"/builds/{bid}/fork")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["forked_from_id"] == bid
    assert body["is_public"] is False
    assert body["data"] == {"v": 1}
    assert "copy" in body["name"].lower()


async def test_create_rejects_unknown_tag(client, db_session):
    await _verified_login(client, db_session, REG)
    r = await client.post("/builds", json={"name": "x", "data": {}, "tags": ["Nope"]})
    assert r.status_code == 422


async def test_like_then_unlike_idempotent(client, db_session):
    await _verified_login(client, db_session, REG)
    created = await client.post("/builds", json={"name": "pub", "data": {}, "is_public": True})
    bid = created.json()["id"]
    await client.post("/auth/logout")
    await _verified_login(client, db_session, REG2)

    r = await client.post(f"/public/builds/{bid}/like")
    assert r.status_code == 200, r.text
    assert r.json() == {"liked": True, "like_count": 1}
    # liking again stays at 1
    r = await client.post(f"/public/builds/{bid}/like")
    assert r.json() == {"liked": True, "like_count": 1}

    d = await client.get(f"/public/builds/{bid}")
    assert d.json()["liked_by_me"] is True
    assert d.json()["like_count"] == 1

    r = await client.delete(f"/public/builds/{bid}/like")
    assert r.json() == {"liked": False, "like_count": 0}
    # unliking again stays at 0
    r = await client.delete(f"/public/builds/{bid}/like")
    assert r.json() == {"liked": False, "like_count": 0}


async def test_like_requires_auth(client, db_session):
    await _verified_login(client, db_session, REG)
    created = await client.post("/builds", json={"name": "pub", "data": {}, "is_public": True})
    bid = created.json()["id"]
    await client.post("/auth/logout")
    r = await client.post(f"/public/builds/{bid}/like")
    assert r.status_code == 401


async def test_like_404_on_non_public(client, db_session):
    await _verified_login(client, db_session, REG)
    created = await client.post("/builds", json={"name": "secret", "data": {}, "is_public": False})
    bid = created.json()["id"]
    r = await client.post(f"/public/builds/{bid}/like")
    assert r.status_code == 404


async def test_is_mine_flag(client, db_session):
    await _verified_login(client, db_session, REG)
    created = await client.post("/builds", json={"name": "pub", "data": {}, "is_public": True})
    bid = created.json()["id"]
    d = await client.get(f"/public/builds/{bid}")
    assert d.json()["is_mine"] is True

    await client.post("/auth/logout")
    await _verified_login(client, db_session, REG2)
    d = await client.get(f"/public/builds/{bid}")
    assert d.json()["is_mine"] is False


async def test_intent_default_pve(client, db_session):
    await _verified_login(client, db_session, REG)
    r = await client.post("/builds", json={"name": "b", "data": {}})
    assert r.status_code == 201
    assert r.json()["intent"] == "pve"


async def test_intent_explicit_and_surfaces_public(client, db_session):
    await _verified_login(client, db_session, REG)
    r = await client.post("/builds", json={"name": "pvp build", "data": {}, "is_public": True, "intent": "pvp"})
    assert r.status_code == 201
    assert r.json()["intent"] == "pvp"
    bid = r.json()["id"]

    public_detail = await client.get(f"/public/builds/{bid}")
    assert public_detail.json()["intent"] == "pvp"
    public_list = await client.get("/public/builds")
    assert any(b["intent"] == "pvp" and b["id"] == bid for b in public_list.json())


async def test_intent_invalid_rejected(client, db_session):
    await _verified_login(client, db_session, REG)
    r = await client.post("/builds", json={"name": "b", "data": {}, "intent": "raid"})
    assert r.status_code == 422


async def test_fork_copies_intent(client, db_session):
    await _verified_login(client, db_session, REG)
    src = await client.post("/builds", json={"name": "Coop heal", "data": {}, "is_public": True, "intent": "coop"})
    bid = src.json()["id"]
    await client.post("/auth/logout")
    await _verified_login(client, db_session, REG2)
    fork = await client.post(f"/builds/{bid}/fork")
    assert fork.status_code == 201
    assert fork.json()["intent"] == "coop"
