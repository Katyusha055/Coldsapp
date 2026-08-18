from fastapi import APIRouter
import backend.contacts.models as mdl
import backend.contacts.service as ser
from backend.auth.utils import CurrentUser

router = APIRouter(
    prefix='/contacts',
    tags=['contacts'],
)


@router.post('/import', response_model=mdl.ImportResult)
async def import_contacts_endpoint(user: CurrentUser):
    return await ser.import_contacts(user['id'])
