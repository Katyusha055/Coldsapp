from fastapi import APIRouter
import backend.clients.models as mdl
import backend.clients.service as ser
from backend.auth.utils import CurrentUser
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/clients',
    tags=['clients'],
)

@router.get('/', response_model=list[mdl.ResponseClient])
def get_clients_endpoint(user: CurrentUser):
    current_user_id = {'user_id': user.id} 
    return ser.get_clients_service(current_user_id)


@router.post('/', response_model=mdl.ResponseClient)
def create_client_endpoint(payload: mdl.CreateClient, user: CurrentUser):
    client_data = {
        **payload.model_dump(),
        "user_id": user.id
    }
    return ser.create_client_service(client_data)

@router.patch('/{client_id}', response_model=mdl.ResponseClient)
def update_client_endpoint(client_id: int, payload: mdl.UpdateClient, user: CurrentUser):
    current_user_id = user.id
    update_data = payload.model_dump(exclude_none=True)
    return ser.update_client_service(current_user_id, client_id, update_data)


@router.delete('/{client_id}')
def delete_client_endpoint(client_id: int, user: CurrentUser):
    current_user_id = user.id
    return ser.delete_client_service(current_user_id, client_id)


@router.get('/{client_id}', response_model=mdl.ResponseClient)
def get_client_by_id_endpoint(client_id: int, user: CurrentUser):
    current_user_id = user.id
    return ser.get_client_by_id_service(current_user_id, client_id)

@router.get('/by-phone/{phone}', response_model=mdl.ResponseClient)
def get_client_by_phone_endpoint(phone: str, user: CurrentUser):
    current_user_id = user.id
    return ser.get_client_by_phone_service(current_user_id, phone)
