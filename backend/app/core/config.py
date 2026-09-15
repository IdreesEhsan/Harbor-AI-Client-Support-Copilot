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

    # Once a conversation grows beyond this number of
    # messages, older messages can be compressed into
    # persistent summary memory.
    memory_summary_threshold: int = 12

    # Monday.com
    #
    # These values are loaded from environment variables.
    # Secrets must never be hardcoded into Harbor's source
    # code or committed to Git.
    monday_api_token: str | None = None
    monday_board_id: str | None = None
    monday_group_id: str | None = None

    # Keeping the API URL configurable makes the integration
    # easier to test and avoids scattering external URLs
    # throughout the application.
    monday_api_url: str = (
        "https://api.monday.com/v2"
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()