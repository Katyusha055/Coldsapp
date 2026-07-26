from backend.core.logging_config import setup_logging
from backend.api.routers import api_router
from backend.middleware import setup_middleware
from fastapi import FastAPI

setup_logging()

app = FastAPI()
app.include_router(api_router)
setup_middleware(app)

