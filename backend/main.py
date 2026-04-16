from backend.core.logging_config import setup_logging
import backend.database.init_db as init

setup_logging()

init.clients_setup()

