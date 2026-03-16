import logging

logger = logging.getLogger(__name__)

def init_db(connect):
    '''
    Initializing the database by creating tables if they are not created yet

    Inputs a psycopg.Connect object 
    '''
    with connect.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS clients (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    phone VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL;

                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                );''')
        cur.execute('''
                    CREATE INDEX IF NOT EXISTS clients_phone_index
                    ON clients(phone)
                ''')
        logger.info('Initialized database succesfully')        
            