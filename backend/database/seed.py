import logging
from connect import connect

logger = logging.getLogger(__name__)

def seed():
    ''''
    Seeds the database with initial data for testing and development purposes.
    '''
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (name, phone, password_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id, name
            """, ('Test User', '0999999999', 'placeholder_hash'))
            
            result = cur.fetchone()
            if result:
                logger.info(f"User created: id={result[0]}, name={result[1]}")
            else:
                logger.info("User already exists, skipping")

if __name__ == "__main__":
    seed()