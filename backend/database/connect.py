import psycopg
import logging
import os 
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
def connect():
    '''
    Connects to database with enviroment variables (.env file)

    Returns a psycopg.Connection object to connect to the database
    '''
    dbname = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    port = os.getenv('DB_PORT')
    host = os.getenv('DB_HOST')
    if not all([dbname, user, password, port, host]):
        raise ValueError("Missing database environment variables")
    try:
        conn = psycopg.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        logger.info(f'Connected with SQL database {dbname} succesfully')
    except Exception as e:
        raise ConnectionError('Connection failed') from e
    return conn
