import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import engine, AsyncSessionLocal


@pytest.mark.asyncio
async def test_engine_can_connect():
    """L'engine async doit pouvoir ouvrir une connexion sur DATABASE_URL."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_session_factory_yields_async_session():
    """AsyncSessionLocal doit produire une AsyncSession utilisable."""
    async with AsyncSessionLocal() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 2"))
        assert result.scalar() == 2
