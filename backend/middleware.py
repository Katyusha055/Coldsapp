from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.settings import settings


def setup_middleware(app: FastAPI) -> None:
    """
    Registers all cross-cutting middleware on the app. Kept out of main.py so
    request/response wiring lives in one place.
    """

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)

        # Unconditional, cheap, and safe on a JSON API.
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        # HSTS is only meaningful (and only safe) over real HTTPS. Gating on
        # both production and the actual request scheme keeps it off local
        # http://localhost dev, where a remembered HSTS policy would otherwise
        # brick the browser. request.url.scheme reads "https" behind Railway's
        # proxy thanks to uvicorn's --proxy-headers.
        if settings.is_production and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )

        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "https://coldsapp.up.railway.app",
        ],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
