from backend.database.connect import connect
from backend.clients.schema import init_db

def clients_setup():
    with connect() as conn:
        init_db(conn)
