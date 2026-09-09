from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str

    model_path: str = "models/plantnova_convnext_cbam.pt"
    storage_bucket: str = "diagnoses"

    # Coordenadas de Lima centro para la consulta de clima.
    clima_lat: float = -12.0464
    clima_lon: float = -77.0428

    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def jwks_url(self) -> str:
        """Endpoint JWKS que expone la clave pública de Supabase Auth."""
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def jwt_issuer(self) -> str:
        """Emisor esperado dentro del token."""
        return f"{self.supabase_url}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    
    return Settings()


settings = get_settings()