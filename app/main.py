import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.activities.router import router as activities_router
from app.modules.auth.router import router as auth_router
from app.modules.diagnoses.model import cargar_modelo
from app.modules.diagnoses.router import router as diagnoses_router
from app.modules.guide.router import router as guide_router
from app.modules.plants.router import router as plants_router
from app.modules.profile.router import router as profile_router
from app.modules.tips.router import router as tips_router
from app.modules.weather.router import router as weather_router

logger = logging.getLogger("plantnova")


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    inicio = time.perf_counter()
    try:
        cargar_modelo()
        logger.info(
            "Modelo cargado en %.1f s", time.perf_counter() - inicio
        )
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo cargar el modelo al arrancar")

    yield


app = FastAPI(
    title="PlantNova API",
    description=(
        "API de diagnóstico fitosanitario para huertos urbanos de "
        "Lima Metropolitana."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(plants_router)
app.include_router(guide_router)
app.include_router(diagnoses_router)
app.include_router(activities_router)
app.include_router(profile_router)
app.include_router(weather_router)
app.include_router(tips_router)


@app.get("/health", tags=["Sistema"], summary="Verifica que la API responde")
def health() -> dict[str, str]:
    
    return {"status": "ok", "environment": settings.environment}
