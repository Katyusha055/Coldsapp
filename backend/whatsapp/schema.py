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
