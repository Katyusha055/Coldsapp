import logging

from backend.core.logging_config import setup_logging
from backend.api.routers import api_router
from backend.middleware import setup_middleware
from backend.settings import settings
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

setup_logging()
logger = logging.getLogger(__name__)

# Hide the interactive docs and schema in production so the API surface is not
# advertised. Toggled by ENV via settings.DOCS_ENABLED.
app = FastAPI(
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)
app.include_router(api_router)
setup_middleware(app)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches anything not already handled (i.e. not an HTTPException, which
    FastAPI handles separately with its intended status/detail). Logs the full
    traceback server-side and returns a generic message so stack traces never
    leak to clients.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

