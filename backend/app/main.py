from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings


settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)


@app.get("/")
def root():
    return {
        "message": "Harbor API is running",
        "environment": settings.app_env,
    }


app.include_router(
    health_router,
    prefix=settings.api_prefix,
    tags=["Health"],
)