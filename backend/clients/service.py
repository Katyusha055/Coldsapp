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
        return rep.update_client(conn, user_id, client_id, data)


def delete_client_service(user_id, client_id):
    payload = {"id": client_id, "user_id": user_id}
    with connect() as conn:
        return rep.delete_client(conn, payload)


def get_client_by_name_service(user_id, client_id):
    payload = {"id": client_id, "user_id": user_id}
    with connect() as conn:
        return rep.get_client_by_id(conn, payload)


def get_client_by_phone_service(user_id, phone):
    payload = {"user_id": user_id, "phone": phone}
    with connect() as conn:
        return rep.get_client_by_phone(conn, payload)
