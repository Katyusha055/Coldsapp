def _row_to_ticket_dict(row) -> dict:
    return {
        "id": row[0],
        "user_id": row[1],
        "client_id": row[2],
        "title": row[3],
        "description": row[4],
        "status": row[5],
        "received_at": str(row[6]) if row[6] else None,
        "ready_at": str(row[7]) if row[7] else None,
        "delivered_at": str(row[8]) if row[8] else None,
        "created_at": str(row[9]),
        "updated_at": str(row[10]),
    }


def get_tickets(conn, data: dict) -> list:
    """
    Returns every ticket for a given user_id.

    Input dict: {"user_id": int}
    Output: list of ResponseTicket-compatible dicts
    """
    user_id = data["user_id"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, client_id, title, description, status,
                   received_at, ready_at, delivered_at, created_at, updated_at
            FROM tickets
            WHERE user_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
    return [_row_to_ticket_dict(row) for row in rows]


def create_ticket(conn, data: dict) -> dict:
    """
    Creates a ticket row.

    Input dict: {"user_id": int, "client_id": int, "title": str, "description": str | None}
    Output dict: ResponseTicket-compatible dict
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tickets (user_id, client_id, title, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id, user_id, client_id, title, description, status,
                      received_at, ready_at, delivered_at, created_at, updated_at
            """,
            (
                data["user_id"],
                data["client_id"],
                data["title"],
                data.get("description"),
            ),
        )
        row = cur.fetchone()
    return _row_to_ticket_dict(row)


def get_ticket_by_id(conn, data: dict) -> dict:
    """
    Gets one ticket by id and user.

    Input dict: {"id": int, "user_id": int}
    Output dict: ResponseTicket-compatible dict, or None if not found
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, client_id, title, description, status,
                   received_at, ready_at, delivered_at, created_at, updated_at
            FROM tickets
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            """,
            (data["id"], data["user_id"]),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_ticket_dict(row)


def delete_ticket(conn, data: dict) -> dict:
    """
    Soft-deletes one ticket by id and user.

    Input dict: {"id": int, "user_id": int}
    Output dict: {"deleted": bool, "id": int}
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE tickets
            SET deleted_at = NOW()
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            RETURNING id
            """,
            (data["id"], data["user_id"]),
        )
        deleted_row = cur.fetchone()
    return {"deleted": deleted_row is not None, "id": data["id"]}


def update_ticket(conn, user_id, ticket_id, data: dict) -> dict:
    """
    Updates one ticket for one user.

    Input dict: {"title": str | None, "description": str | None}
    Output dict: ResponseTicket-compatible dict, or None if not found
    """
    
    set_parts = []
    values = []

    for field, value in data.items():
        set_parts.append(f"{field} = %s")
        values.append(value)

    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)
    values.extend([ticket_id, user_id])

    query = f"""
    UPDATE tickets
    SET {set_clause}
    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
    RETURNING id, user_id, client_id, title, description, status,
              received_at, ready_at, delivered_at, created_at, updated_at
    """

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()

    if row is None:
        return None

    return _row_to_ticket_dict(row)


def update_ticket_status(conn, user_id, ticket_id, status, ready_at=None, delivered_at=None) -> dict:
    """
    Updates the status (and optionally ready_at/delivered_at) of one ticket.

    Output dict: ResponseTicket-compatible dict, or None if not found
    """
    set_parts = ["status = %s", "updated_at = NOW()"]
    values = [status]

    if ready_at is not None:
        set_parts.append("ready_at = %s")
        values.append(ready_at)

    if delivered_at is not None:
        set_parts.append("delivered_at = %s")
        values.append(delivered_at)

    set_clause = ", ".join(set_parts)
    values.extend([ticket_id, user_id])

    query = f"""
    UPDATE tickets
    SET {set_clause}
    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
    RETURNING id, user_id, client_id, title, description, status,
              received_at, ready_at, delivered_at, created_at, updated_at
    """

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()

    if row is None:
        return None

    return _row_to_ticket_dict(row)
