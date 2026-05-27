from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from core import logger, csv_files
from routers import all_routers
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

app = FastAPI(
    title="Elden Ring API",
    description="API pour accéder aux données du dataset Elden Ring",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware pour logger toutes les requêtes."""
    start_time = time.time()
    logger.info(f"Requête entrante: {request.method} {request.url.path}")

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"Requête terminée: {request.method} {request.url.path} - Status: {response.status_code} - Durée: {process_time:.3f}s")

    return response


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enregistrement de tous les routers
for router, prefix, tags in all_routers:
    app.include_router(router, prefix=prefix, tags=tags)


@app.get("/", tags=["Root"])
def root():
    """Point d'entrée de l'API."""
    return {
        "message": "Bienvenue sur l'API Elden Forge",
        "documentation": "/docs",
        "endpoints": list(csv_files)
    }
