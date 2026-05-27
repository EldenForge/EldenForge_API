import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from models.build import Build
from models.email_token import EmailToken
from models.refresh_token import RefreshToken
from models.user import User


async def test_cascade_delete_user_removes_dependents(db_session):
    user = User(email="cas@x.com", pseudo="Cas", password_hash="$argon2id$h")
    db_session.add(user)
    await db_session.flush()

    db_session.add(Build(user_id=user.id, name="b1", data={}))
    db_session.add(
        EmailToken(
            user_id=user.id,
            token_hash="x" * 64,
            purpose="email_verification",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    db_session.add(
        RefreshToken(
            user_id=user.id,
            token_hash="y" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    await db_session.flush()

    # Sanity : 1 row dans chaque table dépendante
    for model in (Build, EmailToken, RefreshToken):
        count = (await db_session.execute(select(model).where(model.user_id == user.id))).all()
        assert len(count) == 1, f"{model.__name__} doit contenir 1 row avant delete"

    # Delete user
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.flush()

    # Tout doit avoir disparu (CASCADE)
    for model in (Build, EmailToken, RefreshToken):
        rows = (await db_session.execute(select(model).where(model.user_id == user.id))).all()
        assert rows == [], f"{model.__name__} doit être vide après delete user"


async def test_user_updated_at_changes_on_modification(db_session):
    user = User(email="upd@x.com", pseudo="Upd", password_hash="$argon2id$h")
    db_session.add(user)
    await db_session.flush()
    created = user.updated_at

    # onupdate ne se déclenche que lors d'un UPDATE explicite — on attend un peu
    await asyncio.sleep(0.01)
    user.pseudo = "Upd2"
    await db_session.flush()
    await db_session.refresh(user)

    assert user.updated_at > created


async def test_build_updated_at_changes_on_modification(db_session):
    user = User(email="upb@x.com", pseudo="Upb", password_hash="$argon2id$h")
    db_session.add(user)
    await db_session.flush()
    build = Build(user_id=user.id, name="b1", data={"v": 1})
    db_session.add(build)
    await db_session.flush()
    created = build.updated_at

    await asyncio.sleep(0.01)
    build.data = {"v": 2}
    await db_session.flush()
    await db_session.refresh(build)

    assert build.updated_at > created
