import psycopg
import logging
from backend.settings import settings

logger = logging.getLogger(__name__)


def connect():
    '''
    Connects to database with settings-provided credentials.

    Returns a psycopg.Connection object to connect to the database
    '''
    try:
        conn = psycopg.connect(
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
        )
        logger.info(f'Connected with SQL database {settings.DB_NAME} succesfully')
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise ConnectionError(f"Connection failed: {str(e)}") from e
    return conn
