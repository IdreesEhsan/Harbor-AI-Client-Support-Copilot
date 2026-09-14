from fastapi import APIRouter, HTTPException

from app.db.supabase import get_supabase_client


router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok"
    }


@router.get("/ready")
def readiness():
    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("users")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "status": "ready",
            "database": "connected"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )