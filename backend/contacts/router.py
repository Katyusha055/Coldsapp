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


@router.get('/', response_model=list[mdl.ContactResponse])
def list_contacts_endpoint(user: CurrentUser):
    return ser.list_contacts(user['id'])


@router.patch('/{contact_id}/name')
def update_contact_name_endpoint(contact_id: int, payload: mdl.ContactNameUpdate, user: CurrentUser):
    return ser.update_contact_name(user['id'], contact_id, payload.name)


@router.patch('/{contact_id}/opted_out')
def update_contact_opted_out_endpoint(contact_id: int, payload: mdl.ContactOptedOutUpdate, user: CurrentUser):
    return ser.update_contact_opted_out(user['id'], contact_id, payload.opted_out)
