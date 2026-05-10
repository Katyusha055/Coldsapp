import logging

logger = logging.getLogger(__name__)

def init_db(connect):
    '''
    Initializing the database by creating the tickets table if not created yet

    Inputs a psycopg.Connect object
    '''
    with connect.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    client_id INTEGER NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in progress', 'ready', 'delivered', 'cancelled')),

                    received_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    ready_at TIMESTAMPTZ DEFAULT NULL,
                    delivered_at TIMESTAMPTZ DEFAULT NULL,
                    deleted_at TIMESTAMPTZ DEFAULT NULL,

                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT fk_tickets_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    CONSTRAINT fk_tickets_client
                        FOREIGN KEY (client_id)
                        REFERENCES clients(id)
                        ON DELETE CASCADE);''')
        cur.execute('''
                    CREATE INDEX IF NOT EXISTS tickets_client_id_index
                    ON tickets(client_id)
                ''')
        cur.execute('''
                    CREATE INDEX IF NOT EXISTS tickets_status_index
                    ON tickets(status)
                ''')
        logger.info('Initialized tickets table successfully')
