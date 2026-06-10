from contextlib import asynccontextmanager
from backend.core.logging_config import setup_logging
import backend.database.init_db as init
from backend.api.routers import api_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init.db_setup()  #is executed once the app is ready to start
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://coldsapp.vercel.app" #TODO: change to actual domain when deployed
    ],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

