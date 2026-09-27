import backend.whatsapp.repository as rep
import backend.shared.repository as shared_rep
from backend.shared.connect import connect
from backend.shared.error_handlers import handle_evo_errors
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_or_create_instance(user_id):
    with connect() as conn:
        instance = shared_rep.get_instance_by_user_id(conn, user_id)
        if instance is not None:
            return instance

        instance_name = f"{user_id}_whatsapp"
        await rep.create_evolution_instance(instance_name)
        return rep.create_instance(conn, user_id, instance_name)

@handle_evo_errors
async def get_qr(user_id):
    instance = await get_or_create_instance(user_id)
    qr = await rep.get_evolution_qr(instance["instance_name"])
    return {"qr": qr}

@handle_evo_errors
async def instance_status(user_id):
    with connect() as conn:
        instance = shared_rep.get_instance_by_user_id(conn, user_id)
    if instance is None:
        return {"status": "not_found"}
    status = await rep.get_evolution_instance_status(instance["instance_name"])
    return {"status": status, "notifications_enabled": instance["notifications_enabled"]}


def set_notifications_enabled(user_id, enabled):
    with connect() as conn:
        instance = shared_rep.get_instance_by_user_id(conn, user_id)
        if instance is None:
            raise HTTPException(status_code=404, detail="WhatsApp instance not found")
        return rep.update_notifications_enabled(conn, instance["id"], enabled)


def handle_connection_event(instance, event, payload):
    """
    Handles the two whatsapp-instance connection webhook events
    (connection.update, qrcode.updated). Called by shared.webhook_dispatch
    after it has already resolved the instance and audited the raw event.
    """
    if event == "connection.update":
        data = payload.get("data", {})
        new_status = data.get("state") or data.get("status")
        with connect() as conn:
            rep.update_instance_status(conn, instance["id"], new_status)
        logger.info(f"Instance {instance['instance_name']} status changed to {new_status}")
        return {"type": "connection_update", "detail": new_status}

    if event == "qrcode.updated":
        logger.info(f"QR code refreshed for instance {instance['instance_name']}")
        return {"type": "qr_updated", "detail": "QR code refreshed"}

    logger.warning(f"handle_connection_event called with unexpected event: {event}")
    return None
