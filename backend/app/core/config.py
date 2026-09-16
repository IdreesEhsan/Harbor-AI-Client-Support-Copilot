from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Harbor API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = True

    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Embeddings
    embedding_model: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    embedding_dimension: int = 384

    # Groq
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Conversation memory
    memory_buffer_size: int = 8
    memory_summary_threshold: int = 12

    # Monday.com integration
    #
    # Monday configuration is optional at application startup.
    # The integration validates these values only when an
    # external Monday operation is requested.
    monday_api_token: str | None = None
    monday_api_url: str = "https://api.monday.com/v2"

    monday_board_id: str | None = None
    monday_group_id: str | None = None

    monday_harbor_ticket_id_column_id: str | None = None
    monday_status_column_id: str | None = None
    monday_idempotency_key_column_id: str | None = None
    monday_description_column_id: str | None = None
    monday_severity_column_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()