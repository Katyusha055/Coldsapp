from fastapi import APIRouter
import backend.clients.models as mdl
import backend.clients.service as ser
from backend.core.auth import get_user_id
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/clients',
    tags=['clients'],
)

@router.get('/', response_model=list[mdl.ResponseClient])
def get_clients_endpoint():
    current_user_id = {'user_id': get_user_id()} #this is to test the program, later i'll replace it with a token and auth system or something like that
    return ser.get_clients_service(current_user_id)


@router.post('/', response_model=mdl.ResponseClient)
def create_client_endpoint(payload: mdl.CreateClient):
    client_data = {
        **payload.model_dump(),
        "user_id": get_user_id()
    }
    return ser.create_client_service(client_data)

@router.patch('/{client_id}', response_model=mdl.ResponseClient)
def update_client_endpoint(client_id: int, payload: mdl.UpdateClient):
    current_user_id = get_user_id()  # mock auth for testing purposes
    update_data = payload.model_dump(exclude_none=True)
    return ser.update_client_service(current_user_id, client_id, update_data)


@router.delete('/{client_id}')
def delete_client_endpoint(client_id: int):
    current_user_id = get_user_id()  # mock auth for testing purposes
    return ser.delete_client_service(current_user_id, client_id)


@router.get('/{client_id}', response_model=mdl.ResponseClient)
def get_client_by_id_endpoint(client_id: int):
    current_user_id = get_user_id()  # mock auth for testing purposes
    return ser.get_client_by_id_service(current_user_id, client_id)

@router.get('/by-phone/{phone}', response_model=mdl.ResponseClient)
def get_client_by_phone_endpoint(phone: str):
    current_user_id = get_user_id()  # mock auth for testing purposes
    return ser.get_client_by_phone_service(current_user_id, phone)
