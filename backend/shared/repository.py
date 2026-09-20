from psycopg.types.json import Jsonb


def _row_to_instance_dict(row) -> dict:
    return {
        "id": row[0],
        "user_id": row[1],
        "instance_name": row[2],
        "status": row[3],
        "created_at": row[4],
        "connected_at": row[5],
        "notifications_enabled": row[6],
    }


def get_instance_by_user_id(conn, user_id):
    """
    Gets one whatsapp instance by user_id.

    Output dict: WhatsAppInstance-compatible dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, instance_name, status, created_at, connected_at, notifications_enabled
            FROM whatsapp_instances
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_instance_dict(row)


def get_instance_by_name(conn, instance_name):
    """
    Gets one whatsapp instance by instance_name.

    Output dict: WhatsAppInstance-compatible dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, instance_name, status, created_at, connected_at, notifications_enabled
            FROM whatsapp_instances
            WHERE instance_name = %s
            """,
            (instance_name,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_instance_dict(row)


def save_event(conn, instance_id, event_type, event_data):
    """
    Saves a whatsapp event row.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO wa_events (instance_id, event_type, event_data)
            VALUES (%s, %s, %s)
            RETURNING id, instance_id, event_type, event_data, created_at
            """,
            (instance_id, event_type, Jsonb(event_data)),
        )
        row = cur.fetchone()
    return {
        "id": row[0],
        "instance_id": row[1],
        "event_type": row[2],
        "event_data": row[3],
        "created_at": row[4],
    }
