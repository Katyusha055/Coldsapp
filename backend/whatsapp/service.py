import backend.whatsapp.repository as rep
from backend.database.connect import connect
from functools import wraps
import httpx
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def handle_evo_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Evolution API timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Evolution API unreachable")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    return wrapper

async def get_or_create_instance(user_id):
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
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
        instance = rep.get_instance_by_user_id(conn, user_id)
    if instance is None:
        return {"status": "not_found"}
    status = await rep.get_evolution_instance_status(instance["instance_name"])
    return {"status": status}


async def process_webhook(payload):
    instance_name = payload.get("instance")
    event = payload.get("event")

    with connect() as conn:
        instance = rep.get_instance_by_name(conn, instance_name)
        if instance is None:
            logger.warning(f"Webhook received for unknown instance: {instance_name}")
            return None

        rep.save_event(conn, instance["id"], event, payload)

        if event == "connection.update":
            data = payload.get("data", {})
            new_status = data.get("state") or data.get("status")
            rep.update_instance_status(conn, instance["id"], new_status)
            logger.info(f"Instance {instance_name} status changed to {new_status}")
            return {"type": "connection_update", "detail": new_status}

        if event == "qrcode.updated":
            logger.info(f"QR code refreshed for instance {instance_name}")
            return {"type": "qr_updated", "detail": "QR code refreshed"}

        if event == "messages.upsert":
            data = payload.get("data", {})

            if data.get("key", {}).get("fromMe"):
                logger.info("Ignoring outgoing message (fromMe=True)")
                return None

            sender = payload.get("sender", "")
            raw_number = sender.replace("@s.whatsapp.net", "")

            if not raw_number.startswith("593"):
                logger.warning(f"Ignoring message from unexpected number prefix: {raw_number}")
                return None

            phone = "0" + raw_number[3:]
            name = data.get("pushName")
            message = data.get("message", {}).get("conversation")
            if not message:
                message = data.get("message", {}).get("extendedTextMessage", {}).get("text")

            user_id = instance["user_id"]
            client = rep.get_client_by_phone(conn, phone, user_id)
            if client is not None:
                logger.info(f"Message from existing client {phone}, ignoring")
                return None

            pending = rep.get_pending_by_phone(conn, phone, instance["id"])
            if pending is None:
                rep.create_pending(conn, instance["id"], phone, name, message)
                return {"type": "new_pending", "phone": phone, "name": name, "message": message}

            if pending["status"] in ("converted", "discarded"):
                return None

            rep.update_pending_message(conn, pending["id"], message)
            return {"type": "pending_update", "phone": phone, "name": name, "message": message}

        logger.info(f"Unhandled webhook event: {event}")
        return None


def set_pending_status(user_id, pending_id, status):
    with connect() as conn:
        pending = rep.get_pending_by_id(conn, pending_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is None or instance["id"] != pending["instance_id"]:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        updated = rep.update_pending_status(conn, pending_id, status)
    return updated


def list_pending_contacts(user_id):
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is None:
            return []
        return rep.get_pending_contacts(conn, instance["id"])


def delete_pending(user_id, pending_id):
    with connect() as conn:
        pending = rep.get_pending_by_id(conn, pending_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is None or instance["id"] != pending["instance_id"]:
            raise HTTPException(status_code=404, detail="Pending contact not found")

        return rep.soft_delete_pending(conn, pending_id)
