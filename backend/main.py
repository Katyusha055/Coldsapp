from contextlib import asynccontextmanager
from backend.core.logging_config import setup_logging
import backend.database.init_db as init
from backend.api.routers import api_router
from fastapi import FastAPI

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init.db_setup()  #is executed once the app is ready to start
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(api_router)

