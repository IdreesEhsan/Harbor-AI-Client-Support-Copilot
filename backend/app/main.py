import logging
import time
from uuid import uuid4

from fastapi import (
    FastAPI,
    Request,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.responses import (
    JSONResponse,
)

from slowapi import (
    _rate_limit_exceeded_handler,
)

from slowapi.errors import (
    RateLimitExceeded,
)

from app.api.agent import (
    router as agent_router,
)

from app.api.auth import (
    router as auth_router,
)

from app.api.conversations import (
    router as conversations_router,
)

from app.api.health import (
    router as health_router,
)

from app.api.rag import (
    router as rag_router,
)

from app.api.realtime import (
    router as realtime_router,
)

from app.api.tickets import (
    router as tickets_router,
)

from app.core.config import (
    get_settings,
)

from app.core.rate_limit import (
    limiter,
)


settings = get_settings()


logging.basicConfig(
    level=getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    ),

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)


logger = logging.getLogger(
    "harbor.api"
)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)


app.state.limiter = (
    limiter
)


app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=(
        settings.get_cors_origins()
    ),

    allow_credentials=True,

    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],

    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Request-ID",
    ],

    expose_headers=[
        "X-Request-ID",
    ],
)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    request_id = (
        request.headers.get(
            "X-Request-ID"
        )
        or str(
            uuid4()
        )
    )


    start_time = (
        time.perf_counter()
    )


    try:
        response = (
            await call_next(
                request
            )
        )

    except Exception:

        duration_ms = (
            (
                time.perf_counter()
                - start_time
            )
            * 1000
        )


        logger.exception(
            (
                "Unhandled request failure | "
                "request_id=%s | "
                "method=%s | "
                "path=%s | "
                "duration_ms=%.2f"
            ),
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )


        raise


    duration_ms = (
        (
            time.perf_counter()
            - start_time
        )
        * 1000
    )


    logger.info(
        (
            "Request completed | "
            "request_id=%s | "
            "method=%s | "
            "path=%s | "
            "status=%s | "
            "duration_ms=%.2f"
        ),
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )


    response.headers[
        "X-Request-ID"
    ] = request_id


    return response


@app.exception_handler(
    Exception
)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = (
        request.headers.get(
            "X-Request-ID"
        )
        or str(
            uuid4()
        )
    )


    logger.exception(
        (
            "Unhandled Harbor exception | "
            "request_id=%s | "
            "method=%s | "
            "path=%s"
        ),
        request_id,
        request.method,
        request.url.path,
    )


    return JSONResponse(
        status_code=500,

        content={
            "detail":
                "An unexpected server error occurred.",

            "request_id":
                request_id,
        },

        headers={
            "X-Request-ID":
                request_id,
        },
    )


@app.get("/")
def root():
    return {
        "name":
            settings.app_name,

        "status":
            "running",

        "environment":
            settings.app_env,

        "version":
            "1.0.0",
    }


app.include_router(
    health_router,
    prefix=settings.api_prefix,
    tags=[
        "Health",
    ],
)


app.include_router(
    auth_router,
    prefix=settings.api_prefix,
    tags=[
        "Authentication",
    ],
)


app.include_router(
    rag_router,
    prefix=settings.api_prefix,
    tags=[
        "RAG",
    ],
)


app.include_router(
    agent_router,
    prefix=settings.api_prefix,
    tags=[
        "Agent",
    ],
)


app.include_router(
    conversations_router,
    prefix=settings.api_prefix,
    tags=[
        "Conversations",
    ],
)


app.include_router(
    realtime_router,
    prefix=settings.api_prefix,
    tags=[
        "Realtime",
    ],
)


app.include_router(
    tickets_router,
    prefix=settings.api_prefix,
    tags=[
        "Tickets",
    ],
)