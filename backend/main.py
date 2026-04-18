from backend.core.logging_config import setup_logging
import backend.database.init_db as init
from backend.api.routers import api_router
from fastapi import FastAPI

setup_logging()

app = FastAPI()
app.include_router(api_router)

init.clients_setup()

