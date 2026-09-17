from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


BACKEND_DIR = (
    Path(__file__).resolve().parents[2]
)

ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # ========================================================
    # Application
    # ========================================================

    app_name: str = "Harbor API"

    app_env: str = "development"

    api_prefix: str = "/api/v1"

    debug: bool = True

    log_level: str = "INFO"

    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    frontend_base_url: str = (
        "http://localhost:5173"
    )

    # ========================================================
    # Rate limiting
    # ========================================================

    general_rate_limit: str = (
        "120/minute"
    )

    agent_rate_limit: str = (
        "20/minute"
    )

    rag_rate_limit: str = (
        "30/minute"
    )

    auth_rate_limit: str = (
        "10/minute"
    )

    # ========================================================
    # LLM usage
    # ========================================================

    llm_max_input_characters: int = (
        4000
    )

    llm_requests_per_user_per_minute: int = (
        20
    )

    # ========================================================
    # Supabase
    # ========================================================

    supabase_url: str

    supabase_service_role_key: str

    supabase_anon_key: str

    # ========================================================
    # Harbor Staff
    # ========================================================

    staff_email: str

    # ========================================================
    # Authentication
    # ========================================================

    jwt_secret_key: str

    jwt_algorithm: str = "HS256"

    jwt_access_token_expire_minutes: int = (
        60
    )

    # ========================================================
    # Embeddings
    # ========================================================

    embedding_model: str = (
        "sentence-transformers/"
        "all-MiniLM-L6-v2"
    )

    embedding_dimension: int = 384

    # ========================================================
    # Groq
    # ========================================================

    groq_api_key: str

    groq_model: str = (
        "llama-3.3-70b-versatile"
    )

    # ========================================================
    # Conversation memory
    # ========================================================

    memory_buffer_size: int = 8

    memory_summary_threshold: int = 12

    # ========================================================
    # Monday.com
    # ========================================================

    monday_api_token: str | None = None

    monday_api_url: str = (
        "https://api.monday.com/v2"
    )

    monday_board_id: str | None = None

    monday_group_id: str | None = None

    monday_harbor_ticket_id_column_id: (
        str | None
    ) = None

    monday_status_column_id: (
        str | None
    ) = None

    monday_idempotency_key_column_id: (
        str | None
    ) = None

    monday_description_column_id: (
        str | None
    ) = None

    monday_severity_column_id: (
        str | None
    ) = None

    # ========================================================
    # n8n
    # ========================================================

    n8n_ticket_webhook_url: (
        str | None
    ) = None

    n8n_webhook_timeout_seconds: float = (
        10.0
    )

    # ========================================================
    # Configuration helpers
    # ========================================================

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_cors_origins(
        self,
    ) -> list[str]:
        origins = [
            origin.strip()
            for origin
            in self.cors_origins.split(",")
            if origin.strip()
        ]

        if not origins:
            raise ValueError(
                "At least one CORS origin "
                "must be configured."
            )

        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()