import asyncio
import os
import time

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session

router = APIRouter()

_DB_TIMEOUT_S = float(os.getenv("HEALTH_DB_TIMEOUT_S", "5.0"))


@router.api_route("", methods=["GET", "HEAD"])
async def health(response: Response, session: AsyncSession = Depends(get_session)):
    """Health check utilisé par UptimeRobot.

    Renvoie 200 si l'app répond et si Neon accepte une requête triviale.
    Renvoie 503 si la base ne répond pas dans le délai imparti. Supporte
    GET et HEAD (le plan gratuit UptimeRobot n'autorise pas le choix de
    la méthode HTTP côté monitor).
    """
    checks: dict[str, dict] = {}
    overall_ok = True

    start = time.perf_counter()
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=_DB_TIMEOUT_S)
        checks["database"] = {
            "status": "ok",
            "backend": "neon",
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
        }
    except asyncio.TimeoutError:
        overall_ok = False
        checks["database"] = {"status": "timeout", "backend": "neon", "timeout_s": _DB_TIMEOUT_S}
    except Exception as exc:
        overall_ok = False
        checks["database"] = {"status": "error", "backend": "neon", "error": type(exc).__name__}

    if not overall_ok:
        response.status_code = 503

    return {
        "status": "ok" if overall_ok else "degraded",
        "checks": checks,
        "version": os.getenv("SENTRY_RELEASE") or "unknown",
    }
