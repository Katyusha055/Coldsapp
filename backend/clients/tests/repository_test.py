from backend.database.connect import connect
from backend.clients import repository as rep

clients_data = [
    {'user_id': '1', 'name': 'Juan', 'phone': '1234567890'},
    {'user_id': '1', 'name': 'Maria', 'phone': '1234567890', 'description': 'She buys a lot'}
    ]

def create_test():
    with connect() as conn:    
        response = []
        for client in clients_data:
            response.append(rep.create_client(conn, client))
            response.append(f'Cliente {client['name']} creado con exito')

        print(response)

def get_clients_test():
    with connect() as conn:
        get_query = {'user_id': '1'}
        response = rep.get_clients(conn, get_query)
        print(response)

def update_client_test():
    with connect() as conn:
        data = {'name': 'Juanita', 'description': 'now its the wife'}
        response = rep.update_client(conn, '1', '2', data)
        print(response)

def delete_client_test():
    with connect() as conn:
        data = {'id': '2', 'user_id': '1'}
        response = rep.delete_client(conn, data)
        print(response)

def get_client_by_phone_test():
    with connect() as conn:
        data = {'user_id': '1', 'phone': '1234567890'}
        response = rep.get_client_by_phone(conn, data)
        print(response)

def get_client_by_id_test():
    with connect() as conn:
        data = {'id': '3', 'user_id': '1'}
        response = rep.get_client_by_id(conn, data)
        print(response)
