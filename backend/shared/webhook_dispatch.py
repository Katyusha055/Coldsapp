import logging

import backend.shared.repository as rep
import backend.pendings.service as pendings_service
from backend.database.connect import connect
from backend.shared.events import push_event

logger = logging.getLogger(__name__)


async def handle_webhook(payload):
    """
    Entry point for every raw Evolution API webhook payload: resolves which
    instance it belongs to, audits the raw event, then routes by event type
    to whichever feature owns that type. Returns the result dict pushed to
    the instance owner's SSE stream, or None when nothing was processed.
    """
    instance_name = payload.get("instance")
    event = payload.get("event")

    with connect() as conn:
        instance = rep.get_instance_by_name(conn, instance_name)
        if instance is None:
            logger.warning(f"Webhook received for unknown instance: {instance_name}")
            return None

        rep.save_event(conn, instance["id"], event, payload)

    if event in ("connection.update", "qrcode.updated"):
        result = pendings_service.handle_connection_event(instance, event, payload)
    elif event == "messages.upsert":
        result = pendings_service.handle_incoming_message(instance, payload)
    else:
        logger.info(f"Unhandled webhook event: {event}")
        return None

    if result is not None:
        await push_event(instance["user_id"], result)
    return result
