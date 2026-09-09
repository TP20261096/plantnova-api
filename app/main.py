from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.plants.router import router as plants_router
from app.modules.guide.router import router as guide_router
from app.modules.diagnoses.router import router as diagnoses_router
from app.modules.activities.router import router as activities_router
from app.modules.profile.router import router as profile_router

app = FastAPI(
    title="PlantNova API",
    description=(
        "API de diagnóstico fitosanitario para huertos urbanos de "
        "Lima Metropolitana."
    ),
    version="1.0.0",
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


@app.get("/health", tags=["Sistema"], summary="Verifica que la API responde")
def health() -> dict[str, str]:
    """Sonda de salud usada por Cloud Run.
 
    Returns:
        Estado del servicio.
    """
    return {"status": "ok", "environment": settings.environment}
