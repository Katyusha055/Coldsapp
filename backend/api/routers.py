from fastapi import APIRouter
from backend.clients.router import router as clients_router

api_router = APIRouter()
api_router.include_router(clients_router)