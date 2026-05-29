from backend.database.connect import connect
from backend.clients.schema import init_db as clients_init_db
from backend.tickets.schema import init_db as tickets_init_db

def db_setup():
    with connect() as conn:
        clients_init_db(conn)
        tickets_init_db(conn)
