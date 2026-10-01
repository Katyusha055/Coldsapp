from functools import wraps
import logging

import httpx
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


def safe_dispatch(feature_name):
    """
    Wraps a messages.upsert dispatch target (instance, payload) -> result so
    a failure in one feature can never affect another dispatched alongside
    it. Catches any exception, logs it at ERROR with enough payload context
    to debug, and returns None instead of re-raising - the webhook always
    responds 200 regardless of what happened here; the error log is the only
    failure signal.
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
