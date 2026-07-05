from backend.database.connect import connect
from backend.clients.schema import init_db as clients_init_db
from backend.tickets.schema import init_db as tickets_init_db
from backend.whatsapp.schema import init_db as whatsapp_init_db, create_wa_pending_contacts_table

def db_setup():
    with connect() as conn:
        clients_init_db(conn)
        tickets_init_db(conn)
        whatsapp_init_db(conn)
        create_wa_pending_contacts_table(conn)
