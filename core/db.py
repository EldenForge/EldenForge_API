import ssl
from typing import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .settings import settings

# Params SSL côté URL qu'on retire pour les remplacer par un SSLContext explicite.
_SSL_QUERY_PARAMS = {"ssl", "sslmode", "sslrootcert", "channel_binding"}


def _engine_url_and_connect_args(raw_url: str) -> tuple[str, dict]:
    """Neon exige TLS mais sans vérification de certificat (= ssl=require).

    On fournit un SSLContext explicite pour qu'asyncpg ne lise AUCUN fichier de
    certificat : sous le sandbox systemd (ProtectHome=true), la lecture du cert
    racine par défaut (~/.postgresql/root.crt) échoue en PermissionError.
    """
    parts = urlsplit(raw_url)
    kept = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _SSL_QUERY_PARAMS]
    clean_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return clean_url, {"ssl": ctx}


_url, _connect_args = _engine_url_and_connect_args(settings.database_url)

engine = create_async_engine(
    _url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI : ouvre une session, la ferme proprement à la fin."""
    async with AsyncSessionLocal() as session:
        yield session
