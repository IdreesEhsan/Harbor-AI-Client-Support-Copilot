from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.core.config import get_settings
from app.db.supabase import get_supabase_client


router = APIRouter()

settings = get_settings()


@router.get("/health")
def health():
    """
    Lightweight liveness endpoint.

    This endpoint does not call external services. It confirms
    that the Harbor FastAPI process is running.
    """

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/ready")
def readiness():
    """
    Readiness endpoint.

    Harbor is considered ready when its required operational
    database connection can successfully perform a minimal
    query.
    """

    try:
        supabase = get_supabase_client()

        (
            supabase
            .table("users")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "status": "ready",
            "database": "connected",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail="Harbor is not ready.",
        ) from exc