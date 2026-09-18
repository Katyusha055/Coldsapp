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
    return {
        "id": row[0],
        "user_id": row[1],
        "instance_name": row[2],
        "status": row[3],
        "created_at": row[4],
        "connected_at": row[5],
        "notifications_enabled": row[6],
    }
