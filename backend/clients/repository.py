from collections.abc import Sequence


def _row_to_client_dict(row: Sequence) -> dict:
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
    conn.commit()
    return _row_to_client_dict(row)


def update_clients(conn, data: dict) -> dict:
    """
    Updates one client for one user.

    Input dict: {"id": int, "user_id": int, "name": str, "phone": str, "description": str | None}
    Output dict: ResponseClient-compatible dict (empty dict when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE clients
            SET name = %s,
                phone = %s,
                description = %s
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, name, phone, description, created_at
            """,
            (
                data["name"],
                data["phone"],
                data.get("description"),
                data["id"],
                data["user_id"],
            ),
        )
        row = cur.fetchone()
    conn.commit()
    if row is None:
        return {}
    return _row_to_client_dict(row)


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
    conn.commit()
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
            ORDER BY id ASC
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
