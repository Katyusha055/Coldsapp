from fastapi import APIRouter
import backend.whatsapp.models as mdl
import backend.whatsapp.service as ser
import backend.shared.events as events
import backend.shared.webhook_dispatch as webhook_dispatch
from backend.auth.utils import CurrentUser, CurrentUserFromQuery
import asyncio
import json
import logging
from fastapi import Request
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/whatsapp',
    tags=['whatsapp'],
)


@router.get('/', response_model=mdl.QrResponse)
async def get_qr_endpoint(user: CurrentUser):
    return await ser.get_qr(user['id'])


@router.get('/status', response_model=mdl.StatusResponse)
async def get_status_endpoint(user: CurrentUser):
    return await ser.instance_status(user['id'])

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()
    result = await webhook_dispatch.handle_webhook(payload)
    if result is None:
        return {"status": "discarded"}
    logger.info(f"Webhook processed: {result}")
    return {"status": "ok", "event": result}


@router.get('/events')
async def whatsapp_events(user: CurrentUserFromQuery):
    queue = asyncio.Queue()
    events.register_queue(user['id'], queue)

    async def generate():
        try:
            while True:
                event = await queue.get()
                yield json.dumps(event)
        finally:
            events.deregister_queue(user['id'])

    return EventSourceResponse(generate())


@router.patch('/notifications')
async def update_notifications_endpoint(payload: mdl.NotificationsToggle, user: CurrentUser):
    return ser.set_notifications_enabled(user['id'], payload.enabled)
