import backend.clients.repository as rep
from backend.database.connect import connect


def get_clients_service(user_id):
    with connect() as conn:
        return rep.get_clients(conn, user_id)