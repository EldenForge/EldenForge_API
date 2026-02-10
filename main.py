from fastapi import FastAPI, Request
import time
from core import logger, csv_files
from routers import all_routers

app = FastAPI(
    title="Elden Ring API",
    description="API pour accéder aux données du dataset Elden Ring",
    version="1.0.0"
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
