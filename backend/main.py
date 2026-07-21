from backend.core.logging_config import setup_logging
from backend.api.routers import api_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

setup_logging()

app = FastAPI()
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://coldsapp.up.railway.app" 
    ],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

