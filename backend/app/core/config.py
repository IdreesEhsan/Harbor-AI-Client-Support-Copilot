from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Harbor API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = True

    supabase_url: str
    supabase_service_role_key: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    embedding_model: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    embedding_dimension: int = 384

    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()