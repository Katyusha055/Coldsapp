from fastapi import APIRouter
import backend.whatsapp.models as mdl
import backend.whatsapp.service as ser
from backend.auth.utils import CurrentUser
import logging
from fastapi import Request

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

import logging
logger = logging.getLogger('uvicorn')
@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()
    result = await ser.process_webhook(payload)
    if result is None:
        return {"status": "discarded"}
    logger.info(f"Webhook processed: {result}")
    return {"status": "ok", "event": result}