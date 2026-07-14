import logging

logger = logging.getLogger(__name__)

def init_db(connect):
    '''
    Initializing the database by creating the whatsapp tables if not created yet

    Inputs a psycopg.Connect object
    '''
    with connect.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS whatsapp_instances (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    instance_name VARCHAR NOT NULL UNIQUE,
                    status VARCHAR NOT NULL DEFAULT 'pending',
                    notifications_enabled BOOLEAN NOT NULL DEFAULT true,

                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    connected_at TIMESTAMPTZ,

                    CONSTRAINT fk_whatsapp_instances_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE);''')
        cur.execute('''CREATE TABLE IF NOT EXISTS wa_events (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER,
                    event_type VARCHAR NOT NULL,
                    event_data JSONB NOT NULL,

                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                    CONSTRAINT fk_wa_events_instance
                        FOREIGN KEY (instance_id)
                        REFERENCES whatsapp_instances(id)
                        ON DELETE CASCADE);''')
        logger.info('Initialized whatsapp tables successfully')


def create_wa_pending_contacts_table(conn):
    '''
    Initializing the database by creating the wa_pending_contacts table if not created yet

    Inputs a psycopg.Connect object
    '''
    with conn.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS wa_pending_contacts (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER NOT NULL,
                    remote_jid VARCHAR NOT NULL,
                    name VARCHAR,
                    last_message TEXT,
                    last_message_at TIMESTAMPTZ,
                    status VARCHAR NOT NULL DEFAULT 'pending',

                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                    UNIQUE(remote_jid, instance_id),
                    CONSTRAINT fk_wa_pending_contacts_instance
                        FOREIGN KEY (instance_id)
                        REFERENCES whatsapp_instances(id)
                        ON DELETE CASCADE);''')
        logger.info('Initialized wa_pending_contacts table successfully')
