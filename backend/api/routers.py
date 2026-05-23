from fastapi import APIRouter
from backend.clients.router import router as clients_router
from backend.tickets.router import router as tickets_router

api_router = APIRouter()
api_router.include_router(clients_router)
api_router.include_router(tickets_router)