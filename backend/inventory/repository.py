from psycopg import sql

UPDATABLE_FIELDS = {"name", "low_stock_threshold"}

# Movements and codes are pre-aggregated per item and then LEFT JOINed, so
# the whole list comes back in one query. Joining both raw tables onto items
# directly would multiply rows (an item with 2 codes would sum its stock twice).
_ITEM_SELECT = """
    SELECT items.id, items.name, items.low_stock_threshold, items.created_at,
           COALESCE(movement_totals.stock, 0) AS stock,
           COALESCE(item_code_lists.codes, ARRAY[]::text[]) AS codes
    FROM items
    LEFT JOIN (
        SELECT item_id, SUM(quantity) AS stock
        FROM stock_movements
        WHERE user_id = %(user_id)s
        GROUP BY item_id
    ) movement_totals ON movement_totals.item_id = items.id
    LEFT JOIN (
        SELECT item_id, array_agg(code::text ORDER BY code) AS codes
        FROM item_codes
        WHERE user_id = %(user_id)s
        GROUP BY item_id
    ) item_code_lists ON item_code_lists.item_id = items.id
    WHERE items.user_id = %(user_id)s AND items.deleted_at IS NULL
"""


def _row_to_item_dict(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "low_stock_threshold": row[2],
        "created_at": row[3],
        "stock": int(row[4]),
        "codes": list(row[5]),
    }


def _row_to_movement_dict(row) -> dict:
    return {
        "id": row[0],
        "quantity": row[1],
        "type": row[2],
        "note": row[3],
        "created_at": row[4],
    }


def list_items(conn, user_id) -> list[dict]:
    """
    Gets every active item of a user, with its stock and linked codes.

    Output: list of item dicts
    """
    with conn.cursor() as cur:
        cur.execute(_ITEM_SELECT + " ORDER BY items.name ASC, items.id ASC", {"user_id": user_id})
        rows = cur.fetchall()
    return [_row_to_item_dict(row) for row in rows]


def get_item(conn, user_id, item_id) -> dict | None:
    """
    Gets one active item of a user, with its stock and linked codes.

    Output dict: item dict (None when missing, deactivated or not the user's)
    """
    with conn.cursor() as cur:
        cur.execute(_ITEM_SELECT + " AND items.id = %(item_id)s", {"user_id": user_id, "item_id": item_id})
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_item_dict(row)


def create_item(conn, user_id, name, low_stock_threshold) -> int:
    """
    Inserts an item row.

    Output: the new item id
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO items (user_id, name, low_stock_threshold)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, name, low_stock_threshold),
        )
        return cur.fetchone()[0]


def update_item(conn, user_id, item_id, data: dict) -> bool:
    """
    Updates one active item of a user.

    Input dict: any subset of UPDATABLE_FIELDS
    Output: True if a row was updated, False otherwise
    Raises ValueError on a key outside UPDATABLE_FIELDS.
    """
    unknown_fields = data.keys() - UPDATABLE_FIELDS
    if unknown_fields:
        raise ValueError(f"Fields not updatable: {sorted(unknown_fields)}")

    set_clause = sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(field)) for field in data)
    query = sql.SQL("""
    UPDATE items
    SET {set_clause}
    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
    RETURNING id
    """).format(set_clause=set_clause)

    with conn.cursor() as cur:
        cur.execute(query, [*data.values(), item_id, user_id])
        return cur.fetchone() is not None


def deactivate_item(conn, user_id, item_id) -> bool:
    """
    Soft-deletes one active item of a user.

    Output: True if a row was deactivated, False otherwise
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE items
            SET deleted_at = NOW()
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            RETURNING id
            """,
            (item_id, user_id),
        )
        return cur.fetchone() is not None


def delete_item_codes(conn, user_id, item_id) -> None:
    """
    Deletes every code linked to one item of a user.
    """
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM item_codes WHERE user_id = %s AND item_id = %s",
            (user_id, item_id),
        )


def insert_movement(conn, user_id, item_id, quantity, movement_type, note=None) -> None:
    """
    Appends one stock movement (signed quantity) for an item of a user.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO stock_movements (user_id, item_id, quantity, type, note)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, item_id, quantity, movement_type, note),
        )


def lock_item_stock(conn, user_id, item_id) -> int | None:
    """
    Locks one active item row of a user (FOR UPDATE, held until the
    transaction ends) and returns its current stock.

    Output: current stock (None when missing, deactivated or not the user's)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM items
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            FOR UPDATE
            """,
            (item_id, user_id),
        )
        if cur.fetchone() is None:
            return None
        cur.execute(
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM stock_movements
            WHERE user_id = %s AND item_id = %s
            """,
            (user_id, item_id),
        )
        return int(cur.fetchone()[0])


def list_movements(conn, user_id, item_id) -> list[dict]:
    """
    Gets the movement history of one item of a user, newest first.

    Output: list of movement dicts
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, quantity, type, note, created_at
            FROM stock_movements
            WHERE user_id = %s AND item_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (user_id, item_id),
        )
        rows = cur.fetchall()
    return [_row_to_movement_dict(row) for row in rows]


def get_item_id_by_code(conn, user_id, code) -> int | None:
    """
    Finds the active item of a user that a (normalized) code is linked to.

    Output: item id (None when the code is not linked)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT item_codes.item_id
            FROM item_codes
            JOIN items ON items.id = item_codes.item_id AND items.user_id = item_codes.user_id
            WHERE item_codes.user_id = %s AND item_codes.code = %s AND items.deleted_at IS NULL
            """,
            (user_id, code),
        )
        row = cur.fetchone()
    return row[0] if row else None


def link_code(conn, user_id, item_id, code) -> bool:
    """
    Links a (normalized) code to one item of a user.

    Output: True if linked, False if the user already has that code linked
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO item_codes (user_id, item_id, code)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, code) DO NOTHING
            RETURNING id
            """,
            (user_id, item_id, code),
        )
        return cur.fetchone() is not None


def unlink_code(conn, user_id, item_id, code) -> bool:
    """
    Unlinks (hard-deletes) a (normalized) code from one item of a user.

    Output: True if a code was removed, False otherwise
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM item_codes
            WHERE user_id = %s AND item_id = %s AND code = %s
            RETURNING id
            """,
            (user_id, item_id, code),
        )
        return cur.fetchone() is not None
