from fastapi import FastAPI
from app.api.rag import router as rag_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.api.auth import router as auth_router
from app.api.agent import router as agent_router

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

app.include_router(
    auth_router,
    prefix=settings.api_prefix,
    tags=["Authentication"],
)

app.include_router(
    rag_router,
    prefix=settings.api_prefix,
)

app.include_router(
    agent_router,
    prefix=settings.api_prefix,
)