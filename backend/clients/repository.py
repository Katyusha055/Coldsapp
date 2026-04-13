import psycopg

def get_clients(conn, user_id = str):
    '''
    Reads the clients table and returns clients list
    Inputs: user_id, psycopg.connect object
    Outputs: clients list
    '''
    with conn.cursor() as cur:
        cur.execute()

def update_clients():
    pass

def delete_clients():
    pass

def create_clients():
    pass

def get_clients_by_phone():
    pass

def get_clients_by_id():
    pass