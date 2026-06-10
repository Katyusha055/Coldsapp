def row_to_dict(cursor, row):
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def get_user_by_phone(conn, phone: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, phone FROM users WHERE phone = %s",
            (phone,)
        )
        return row_to_dict(cur, cur.fetchone())


def get_user_credentials(conn, phone: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, password_hash FROM users WHERE phone = %s",
            (phone,)
        )
        return row_to_dict(cur, cur.fetchone())


def get_user_by_id(conn, user_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, phone FROM users WHERE id = %s",
            (user_id,)
        )
        return row_to_dict(cur, cur.fetchone())


def create_user(conn, user_data: dict) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (name, phone, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id, name, phone
            """,
            (user_data["name"], user_data["phone"], user_data["password_hash"])
        )
        row = cur.fetchone()
        return row_to_dict(cur, row)