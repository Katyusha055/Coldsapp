def _row_to_client_dict(row: dict) -> dict:
    return {
        "id": row[0],
        "user_id": row[1],
        "name": row[2],
        "phone": row[3],
        "description": row[4],
        "created_at": str(row[5]),
    }


def get_clients(conn, data: dict) -> dict:
    """
    Returns every client for a given user_id.

    Input dict: {"user_id": int}
    Output dict: {"items": [ResponseClient-compatible dict, ...]}
    """
    user_id = data["user_id"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, name, phone, description, created_at
            FROM clients
            WHERE user_id = %s
            ORDER BY id ASC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
    return {"items": [_row_to_client_dict(row) for row in rows]}


def create_clients(conn, data: dict) -> dict:
    """
    Creates a client row.

    Input dict: {"user_id": int, "name": str, "phone": str, "description": str | None}
    Output dict: ResponseClient-compatible dict
    """
    payload = {
        "user_id": data["user_id"],
        "name": data["name"],
        "phone": data["phone"],
        "description": data.get("description"),
    }

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO clients (user_id, name, phone, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id, user_id, name, phone, description, created_at
            """,
            (
                payload["user_id"],
                payload["name"],
                payload["phone"],
                payload["description"],
            ),
        )
        row = cur.fetchone()
    return _row_to_client_dict(row)


def update_clients(conn, user_id, client_id, data: dict) -> dict:
    """
    Updates one client for one user.

    Input dict: {"id": int, "user_id": int, "name": str, "phone": str, "description": str | None}
    Output dict: ResponseClient-compatible dict (empty dict when not found)
    """
    with conn.cursor() as cur:
        allowed_fields = ['name', 'phone', 'description']

        filtered_data = {
            key: value
            for key, value in data.items()
            if key in allowed_fields and value is not None
        }

        if not filtered_data:
            raise ValueError('No valid fields provided for update')
        
        set_parts = []
        values = []

        for field, value, in filtered_data.items():
            set_parts.append(f'{field} = %s')
            values.append(value)

        set_clause = ', '.join(set_parts)
        #print(set_clause)
        values.extend([client_id, user_id])
        #print(values)

        query = f'''
        UPDATE clients 
        SET {set_clause}
        WHERE id = %s AND user_id = %s
        RETURNING id, user_id, name, phone, description, created_at
        '''
    
        #print(type(query))
        response = {}
        cur.execute(query, values)
        row = cur.fetchone()
        response = _row_to_client_dict(row)

        if row is None:
            return None
        
        return response
        

def delete_clients(conn, data: dict) -> dict:
    """
    Deletes one client by id and user.

    Input dict: {"id": int, "user_id": int}
    Output dict: {"deleted": bool, "id": int}
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM clients
            WHERE id = %s AND user_id = %s
            RETURNING id
            """,
            (data["id"], data["user_id"]),
        )
        deleted_row = cur.fetchone()
    return {"deleted": deleted_row is not None, "id": data["id"]}


def get_clients_by_phone(conn, data: dict) -> dict:
    """
    Gets one client by phone and user.

    Input dict: {"user_id": int, "phone": str}
    Output dict: ResponseClient-compatible dict (empty dict when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, name, phone, description, created_at
            FROM clients
            WHERE user_id = %s AND phone = %s
            LIMIT 1
            """,
            (data["user_id"], data["phone"]),
        )
        row = cur.fetchone()
    if row is None:
        return {}
    return _row_to_client_dict(row)


def get_clients_by_id(conn, data: dict) -> dict:
    """
    Gets one client by id and user.

    Input dict: {"id": int, "user_id": int}
    Output dict: ResponseClient-compatible dict (empty dict when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, name, phone, description, created_at
            FROM clients
            WHERE id = %s AND user_id = %s
            """,
            (data["id"], data["user_id"]),
        )
        row = cur.fetchone()
    if row is None:
        return {}
    return _row_to_client_dict(row)
