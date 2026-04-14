from backend.core.logging_config import setup_logging
import backend.database.init_db as init

setup_logging()

init.clients_setup()

#import backend.clients.service as service

#service.create_test()
#service.get_clients_test()
#service.update_client_test()
#service.delete_client_test()
#service.get_client_by_phone_test()
#service.get_client_by_id_test()