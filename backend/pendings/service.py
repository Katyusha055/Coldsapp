import backend.pendings.repository as rep
import backend.shared.repository as shared_rep
from backend.database.connect import connect
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
    Handles the two whatsapp-instance connection webhook events. Called by
    shared.webhook_dispatch after it has already resolved the instance and
    audited the raw event.
    """
    with connect() as conn:
        if event == "connection.update":
            data = payload.get("data", {})
            new_status = data.get("state") or data.get("status")
            rep.update_instance_status(conn, instance["id"], new_status)
            logger.info(f"Instance {instance['instance_name']} status changed to {new_status}")
            return {"type": "connection_update", "detail": new_status}

        logger.info(f"QR code refreshed for instance {instance['instance_name']}")
        return {"type": "qr_updated", "detail": "QR code refreshed"}


def handle_incoming_message(instance, payload):
    """
    Handles a messages.upsert webhook event: matches it against an existing
    client, and if it doesn't match, creates or updates a pending contact.
    Called by shared.webhook_dispatch after it has already resolved the
    instance and audited the raw event.
    """
    data = payload.get("data", {})

    if data.get("key", {}).get("fromMe"):
        logger.info("Ignoring outgoing message (fromMe=True)")
        return None

    remote_jid = data.get("key", {}).get("remoteJid")
    name = data.get("pushName")
    message = data.get("message", {}).get("conversation")
    if not message:
        message = data.get("message", {}).get("extendedTextMessage", {}).get("text")

    user_id = instance["user_id"]

    with connect() as conn:
        client = rep.get_client_by_whatsapp_id(conn, remote_jid, user_id)
        if client is not None:
            logger.info(f"Message from existing client {remote_jid}, ignoring")
            return None

        pending = rep.get_pending_by_remote_jid(conn, remote_jid, instance["id"])
        result = None
        if pending is None:
            created = rep.create_pending(conn, instance["id"], remote_jid, name, message)
            if created is None:
                # Lost a race with a concurrent webhook delivery for the same
                # contact; fall back to treating it as an update.
                pending = rep.get_pending_by_remote_jid(conn, remote_jid, instance["id"])
            else:
                result = {"type": "new_pending", "id": created["id"], "remote_jid": remote_jid, "name": name, "message": message}

        if result is None:
            if pending is None or pending["status"] in ("converted", "discarded"):
                return None
            rep.update_pending_message(conn, pending["id"], message)
            result = {"type": "pending_update", "remote_jid": remote_jid, "name": name, "message": message}

    return result


def set_pending_status(user_id, pending_id, status):
    with connect() as conn:
        pending = rep.get_pending_by_id(conn, pending_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        instance = shared_rep.get_instance_by_user_id(conn, user_id)
        if instance is None or instance["id"] != pending["instance_id"]:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        updated = rep.update_pending_status(conn, pending_id, status)
    return updated


def list_pending_contacts(user_id):
    with connect() as conn:
        instance = shared_rep.get_instance_by_user_id(conn, user_id)
        if instance is None:
            return []
        return rep.get_pending_contacts(conn, instance["id"])


def delete_pending(user_id, pending_id):
    with connect() as conn:
        pending = rep.get_pending_by_id(conn, pending_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        instance = shared_rep.get_instance_by_user_id(conn, user_id)
        if instance is None or instance["id"] != pending["instance_id"]:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        return rep.delete_pending(conn, pending_id)
