import backend.whatsapp.repository as rep
from backend.database.connect import connect
from functools import wraps
import asyncio
import httpx
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# In-memory SSE queues, one per user_id. Last connection wins if a user opens
# multiple tabs. Not shared across processes.
queues: dict[int, asyncio.Queue] = {}


def register_queue(user_id, queue):
    queues[user_id] = queue


def deregister_queue(user_id):
    queues.pop(user_id, None)


async def push_event(user_id, event):
    queue = queues.get(user_id)
    if queue is not None:
        await queue.put(event)

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
        result = None

        if event == "connection.update":
            data = payload.get("data", {})
            new_status = data.get("state") or data.get("status")
            rep.update_instance_status(conn, instance["id"], new_status)
            logger.info(f"Instance {instance_name} status changed to {new_status}")
            result = {"type": "connection_update", "detail": new_status}

        elif event == "qrcode.updated":
            logger.info(f"QR code refreshed for instance {instance_name}")
            result = {"type": "qr_updated", "detail": "QR code refreshed"}

        elif event == "messages.upsert":
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
            client = rep.get_client_by_whatsapp_id(conn, remote_jid, user_id)
            if client is not None:
                logger.info(f"Message from existing client {remote_jid}, ignoring")
                return None

            pending = rep.get_pending_by_remote_jid(conn, remote_jid, instance["id"])
            if pending is None:
                created = rep.create_pending(conn, instance["id"], remote_jid, name, message)
                if created is None:
                    # Lost a race with a concurrent webhook delivery for the same
                    # contact; fall back to treating it as an update.
                    pending = rep.get_pending_by_remote_jid(conn, remote_jid, instance["id"])
                else:
                    result = {"type": "new_pending", "remote_jid": remote_jid, "name": name, "message": message}

            if result is None:
                if pending is None or pending["status"] in ("converted", "discarded"):
                    return None
                rep.update_pending_message(conn, pending["id"], message)
                result = {"type": "pending_update", "remote_jid": remote_jid, "name": name, "message": message}

        else:
            logger.info(f"Unhandled webhook event: {event}")

    if result is not None:
        await push_event(instance["user_id"], result)
    return result


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

        return rep.delete_pending(conn, pending_id)
