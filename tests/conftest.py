"""Fixtures partagées pour les tests de la couche persistance.

Stratégie :
- Une seule database de test (eldenforge_test), créée si absente (best-effort).
- Schéma monté une fois par session pytest via Base.metadata.create_all
  (les extensions citext / pgcrypto sont créées avant).
- Chaque test tourne dans une transaction qui est rollback à la fin → isolation totale.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.settings import settings
from models import Base

# Importer ici tous les modèles pour qu'ils soient enregistrés sur Base.metadata
# avant que create_all soit appelé. Ajouter les imports au fur et à mesure des tâches.
from models.user import User  # noqa: F401
from models.build import Build  # noqa: F401
from models.build_like import BuildLike  # noqa: F401
from models.email_token import EmailToken  # noqa: F401
from models.refresh_token import RefreshToken  # noqa: F401


def _ensure_test_database_exists(test_url: str) -> None:
    """Crée la database de test si elle n'existe pas (via la DB 'postgres' admin).

    Best-effort : si psycopg n'est pas installé ou si la connexion admin échoue
    (cas typique sur Neon où on peut ne pas avoir les droits CREATE DATABASE
    depuis un client distant), on silence l'erreur et on suppose que la DB existe déjà.
    """
    try:
        import psycopg  # type: ignore
    except ImportError:
        return

    parsed = urlparse(test_url.replace("postgresql+asyncpg", "postgresql"))
    db_name = parsed.path.lstrip("/")
    # Sur Neon, l'URL contient ?ssl=require qu'il faut traduire en sslmode=require pour psycopg
    admin_url = urlunparse(parsed._replace(path="/postgres", query="sslmode=require"))

    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                if cur.fetchone() is None:
                    cur.execute(f'CREATE DATABASE "{db_name}"')
    except Exception:
        # DB existe déjà ou pas les droits — on continue, les tests planteront
        # plus tard si la DB n'existe vraiment pas.
        pass


@pytest.fixture(scope="session")
def event_loop():
    """Event loop unique pour toute la session (compat fixtures session-scoped)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Engine async pointant sur TEST_DATABASE_URL. Schéma monté au début, droppé à la fin."""
    assert settings.test_database_url, "TEST_DATABASE_URL doit être défini dans .env"

    _ensure_test_database_exists(settings.test_database_url)

    engine = create_async_engine(settings.test_database_url, echo=False, pool_pre_ping=True)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session par test, encadrée d'une transaction rollback-only → isolation parfaite."""
    connection = await async_engine.connect()
    trans = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()
    await session.begin_nested()  # SAVEPOINT — allows session.commit() without releasing outer transaction

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


# ─── Fixtures pour tests d'intégration HTTP ───────────────────────────────────

import httpx
from httpx import ASGITransport


class _EmailSink:
    """Collecteur d'emails pour les tests — remplace le ConsoleEmailSender."""

    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, to: str, subject: str, html_body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "html": html_body})


@pytest_asyncio.fixture
async def email_sink():
    return _EmailSink()


@pytest_asyncio.fixture
async def client(db_session, email_sink):
    """httpx AsyncClient avec get_session et email_sender overridés."""
    from main import app
    from core.db import get_session

    async def _override_get_session():
        yield db_session

    # Override the sender imported by the router
    import routers.auth as auth_router_module
    original_sender = auth_router_module.email_sender
    auth_router_module.email_sender = email_sink

    app.dependency_overrides[get_session] = _override_get_session

    # Reset slowapi limiter to isolate tests (rate limit storage is module-level in-memory)
    try:
        lim = auth_router_module.limiter
        if hasattr(lim, "reset"):
            lim.reset()
        elif hasattr(lim, "_storage"):
            storage = lim._storage
            if hasattr(storage, "reset"):
                storage.reset()
            elif hasattr(storage, "storage"):
                storage.storage.clear()
    except Exception:
        pass  # best-effort — don't fail tests if reset internals change

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Cleanup
    app.dependency_overrides.clear()
    auth_router_module.email_sender = original_sender
