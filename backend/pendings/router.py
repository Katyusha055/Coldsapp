from fastapi import APIRouter
import backend.pendings.models as mdl
import backend.pendings.service as ser
from backend.auth.utils import CurrentUser

router = APIRouter(
    prefix='/whatsapp',
    tags=['whatsapp'],
)


@router.patch('/pending/{pending_id}/status')
async def update_pending_status_endpoint(pending_id: int, payload: mdl.PendingStatusUpdate, user: CurrentUser):
    return ser.set_pending_status(user['id'], pending_id, payload.status)


@router.get('/pending')
async def list_pending_contacts_endpoint(user: CurrentUser):
    return ser.list_pending_contacts(user['id'])


@router.delete('/pending/{pending_id}')
async def delete_pending_endpoint(pending_id: int, user: CurrentUser):
    return ser.delete_pending(user['id'], pending_id)
