from datetime import datetime, timezone
import httpx
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


def _format_ecuador_phone(phone: str) -> str:
    """
    Ecuador-formats a phone for the Evolution API: strip a single leading 0
    and prepend 593 (e.g. "0987654321" -> "593987654321").
    """
    return "593" + (phone[1:] if phone.startswith("0") else phone)


def create_ticket(user_id, data: dict) -> TicketResponse:
    with connect() as conn:
        client = clients_rep.get_client_by_id(conn, {"id": data["client_id"], "user_id": user_id})
        if client is None:
            raise HTTPException(status_code=404, detail="Client not found")
        ticket = rep.create_ticket(conn, {**data, "user_id": user_id})
    return ticket


def get_tickets(user_id) -> list[TicketResponse]:
    with connect() as conn:
        tickets = rep.get_tickets(conn, {"user_id": user_id})
    return tickets


def get_ticket_by_id(user_id, ticket_id) -> TicketResponse:
    with connect() as conn:
        ticket = rep.get_ticket_by_id(conn, {"id": ticket_id, "user_id": user_id})
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def delete_ticket(user_id, ticket_id) -> None:
    with connect() as conn:
        result = rep.delete_ticket(conn, {"id": ticket_id, "user_id": user_id})
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail="Ticket not found")


def update_ticket(user_id, ticket_id, data: dict) -> TicketResponse:
    if all(v is None for v in data.values()):
        raise HTTPException(status_code=400, detail="No fields to update")
    
    allowed_fields = ["title", "description"]
    filtered_data = {
        key: value
        for key, value in data.items()
        if key in allowed_fields and value is not None
    }

    if not filtered_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    with connect() as conn:
        ticket = rep.update_ticket(conn, user_id, ticket_id, filtered_data)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


async def notify_ticket_ready(user_id, ticket) -> dict:
    """
    Sends the "ready" WhatsApp notification for a ticket's client.

    Returns a dict with the two notification fields to attach to the ticket:
    {"whatsapp_notification_sent": bool, "whatsapp_notification_error": str | None}.

    Never notifies when the instance is missing or has notifications disabled.
    Raises HTTPException (504/503/Evo status) if the Evolution API call itself
    fails, so the caller can abort before persisting the status change.
    """
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
        client = None
        if instance is not None:
            client = rep.get_client_by_id(conn, {"id": ticket["client_id"], "user_id": user_id})

    if instance is None or not instance["notifications_enabled"]:
        return {"whatsapp_notification_sent": False, "whatsapp_notification_error": None}

    if client is None or not client.get("phone"):
        return {"whatsapp_notification_sent": False, "whatsapp_notification_error": "client_has_no_phone"}

    number = _format_ecuador_phone(client["phone"])

    try:
        await rep.send_whatsapp_message(
            instance["instance_name"],
            number,
            f"Hola {client['name']}, tu equipo está listo para retirar.",
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Evolution API timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Evolution API unreachable")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    return {"whatsapp_notification_sent": True, "whatsapp_notification_error": None}


async def update_ticket_status(user_id, ticket_id, new_status: str) -> TicketResponse:
    current_ticket = get_ticket_by_id(user_id, ticket_id)
    current_status = current_ticket["status"]

    if new_status not in VALID_TRANSITIONS[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current_status} to {new_status}"
        )

    ready_at = None
    delivered_at = None
    notification = None

    if new_status == "ready":
        ready_at = datetime.now(timezone.utc)
        # Notify before persisting: if the Evolution API fails this raises and
        # the status is never saved, so the client can safely retry.
        notification = await notify_ticket_ready(user_id, current_ticket)
    elif new_status == "delivered":
        delivered_at = datetime.now(timezone.utc)

    with connect() as conn:
        ticket = rep.update_ticket_status(conn, user_id, ticket_id, new_status, ready_at, delivered_at)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if notification is not None:
        ticket["whatsapp_notification_sent"] = notification["whatsapp_notification_sent"]
        ticket["whatsapp_notification_error"] = notification["whatsapp_notification_error"]
    return ticket
