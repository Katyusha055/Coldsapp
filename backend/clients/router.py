from fastapi import APIRouter
import backend.clients.models as mdl
import backend.clients.service as ser
from backend.core.auth import get_user_id

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
    current_user_id = {'user_id': get_user_id()} #this is to test the program, later i'll replace it with a token and auth system or something like that
    client_data = {
        **payload.model_dump(),
        "user_id": current_user_id["user_id"],
    }
    return ser.create_client_service(client_data)
