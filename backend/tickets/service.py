from datetime import datetime, timezone
from fastapi import HTTPException
import backend.tickets.repository as rep
import backend.clients.repository as clients_rep
from backend.database.connect import connect
from backend.tickets.models import TicketResponse

VALID_TRANSITIONS = {
    "pending":     ["in_progress", "cancelled"],
    "in_progress": ["ready", "cancelled"],
    "ready":       ["delivered", "cancelled"],
    "delivered":   [],
    "cancelled":   []
}


def create_ticket(user_id, data: dict) -> TicketResponse:
    with connect() as conn:
        client = clients_rep.get_client_by_id(conn, {"id": data["client_id"], "user_id": user_id})
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found")
        ticket = rep.create_ticket(conn, {**data, "user_id": user_id})
    return TicketResponse(**ticket)


def get_tickets(user_id) -> list[TicketResponse]:
    with connect() as conn:
        tickets = rep.get_tickets(conn, {"user_id": user_id})
    return [TicketResponse(**t) for t in tickets]


def get_ticket_by_id(user_id, ticket_id) -> TicketResponse:
    with connect() as conn:
        ticket = rep.get_ticket_by_id(conn, {"id": ticket_id, "user_id": user_id})
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse(**ticket)


def delete_ticket(user_id, ticket_id) -> None:
    with connect() as conn:
        result = rep.delete_ticket(conn, {"id": ticket_id, "user_id": user_id})
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail="Ticket not found")


def update_ticket(user_id, ticket_id, data: dict) -> TicketResponse:
    if all(v is None for v in data.values()):
        raise HTTPException(status_code=400, detail="No fields to update")
    with connect() as conn:
        ticket = rep.update_ticket(conn, user_id, ticket_id, data)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse(**ticket)


def update_ticket_status(user_id, ticket_id, new_status: str) -> TicketResponse:
    current_ticket = get_ticket_by_id(user_id, ticket_id)
    current_status = current_ticket.status

    if new_status not in VALID_TRANSITIONS[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current_status} to {new_status}"
        )

    ready_at = None
    delivered_at = None

    if new_status == "ready":
        ready_at = datetime.now(timezone.utc)
    elif new_status == "delivered":
        delivered_at = datetime.now(timezone.utc)

    with connect() as conn:
        ticket = rep.update_ticket_status(conn, user_id, ticket_id, new_status, ready_at, delivered_at)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse(**ticket)
