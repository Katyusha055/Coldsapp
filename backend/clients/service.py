from fastapi import HTTPException
import backend.clients.repository as rep
from backend.database.connect import connect


def get_clients_service(user_id):
    with connect() as conn:
        return rep.get_clients(conn, user_id)


def create_client_service(data):
    with connect() as conn:
        return rep.create_client(conn, data)


def update_client_service(user_id, client_id, data):
    with connect() as conn:
        allowed_fields = ["name", "phone", "description"]

        filtered_data = {
            key: value
            for key, value in data.items()
            if key in allowed_fields and value is not None
        }

        if not filtered_data:
            raise HTTPException(status_code=422, detail="No valid fields provided for update")
        response = rep.update_client(conn, user_id, client_id, data)
        if response is None:
            raise HTTPException(status_code=404, detail="Client not found")
        return response


def delete_client_service(user_id, client_id):
    payload = {"id": client_id, "user_id": user_id}
    with connect() as conn:
        return rep.delete_client(conn, payload)


def get_client_by_id_service(user_id, client_id):
    payload = {"id": client_id, "user_id": user_id}
    with connect() as conn:
        response = rep.get_client_by_id(conn, payload)
        if response is None:
            raise HTTPException(status_code=404, detail="Client not found")
        return response


def get_client_by_phone_service(user_id, phone):
    payload = {"user_id": user_id, "phone": phone}
    with connect() as conn:
        response = rep.get_client_by_phone(conn, payload)
        if response is None:
            raise HTTPException(status_code=404, detail="Client not found")
        return response