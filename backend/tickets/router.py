from fastapi import APIRouter, Response
import backend.tickets.models as mdl
import backend.tickets.service as ser
from backend.core.auth import get_user_id

router = APIRouter(
    prefix='/tickets',
    tags=['tickets'],
)


@router.post('/', response_model=mdl.TicketResponse)
def create_ticket_endpoint(payload: mdl.TicketCreate):
    current_user_id = get_user_id()
    return ser.create_ticket(current_user_id, payload.model_dump())


@router.get('/', response_model=list[mdl.TicketResponse])
def get_tickets_endpoint():
    current_user_id = get_user_id()
    return ser.get_tickets(current_user_id)


@router.get('/{ticket_id}', response_model=mdl.TicketResponse)
def get_ticket_by_id_endpoint(ticket_id: int):
    current_user_id = get_user_id()
    return ser.get_ticket_by_id(current_user_id, ticket_id)


@router.delete('/{ticket_id}', status_code=204)
def delete_ticket_endpoint(ticket_id: int):
    current_user_id = get_user_id()
    ser.delete_ticket(current_user_id, ticket_id)
    return Response(status_code=204)


@router.patch('/{ticket_id}/status', response_model=mdl.TicketResponse)
def update_ticket_status_endpoint(ticket_id: int, payload: mdl.TicketStatusUpdate):
    current_user_id = get_user_id()
    return ser.update_ticket_status(current_user_id, ticket_id, payload.status)


@router.patch('/{ticket_id}', response_model=mdl.TicketResponse)
def update_ticket_endpoint(ticket_id: int, payload: mdl.TicketUpdate):
    current_user_id = get_user_id()
    return ser.update_ticket(current_user_id, ticket_id, payload.model_dump())
