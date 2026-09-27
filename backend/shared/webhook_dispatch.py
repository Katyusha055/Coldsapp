from functools import wraps
import logging

import backend.shared.repository as rep
import backend.whatsapp.service as whatsapp_service
import backend.pendings.service as pendings_service
import backend.contacts.service as contacts_service
from backend.shared.connect import connect
from backend.shared.events import push_event

logger = logging.getLogger(__name__)


def safe_dispatch(feature_name):
    """
    Wraps a messages.upsert dispatch target so a failure in one feature can
    never affect another. Catches any exception, logs it at ERROR with
    enough payload context to debug, and returns None instead of re-raising
    - the webhook always responds 200 regardless of what happened here; the
    error log is the only failure signal.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(instance, payload):
            try:
                return func(instance, payload)
            except Exception:
                remote_jid = payload.get("data", {}).get("key", {}).get("remoteJid")
                logger.error(
                    "[webhook:messages.upsert] %s dispatch failed (remote_jid=%s, instance_id=%s)",
                    feature_name, remote_jid, instance.get("id"),
                    exc_info=True,
                )
                return None
        return wrapper
    return decorator


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
        result = whatsapp_service.handle_connection_event(instance, event, payload)
    elif event == "messages.upsert":
        # Two independent features react to the same event; neither knows
        # about the other, and a failure in one must never block the other.
        safe_dispatch("contacts")(contacts_service.handle_incoming_message)(instance, payload)
        result = safe_dispatch("pendings")(pendings_service.handle_incoming_message)(instance, payload)
    else:
        logger.info(f"Unhandled webhook event: {event}")
        return None

    if result is not None:
        await push_event(instance["user_id"], result)
    return result
