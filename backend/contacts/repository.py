import httpx
from backend.settings import settings

EVO_API_URL = settings.EVO_API_URL
EVO_API_TOKEN = settings.EVO_API_TOKEN


async def find_contacts(instance_name: str) -> list[dict]:
    """
    Calls the Evolution API to fetch all contacts for an instance.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{EVO_API_URL}/chat/findContacts/{instance_name}",
            headers={"apikey": EVO_API_TOKEN},
            json={},
        )
        response.raise_for_status()
        return response.json()


async def find_chats(instance_name: str) -> list[dict]:
    """
    Calls the Evolution API to fetch all chats for an instance.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{EVO_API_URL}/chat/findChats/{instance_name}",
            headers={"apikey": EVO_API_TOKEN},
            json={},
        )
        response.raise_for_status()
        return response.json()


def _row_to_contact_dict(row) -> dict:
    return {
        "id": row[0],
        "instance_id": row[1],
        "remote_jid": row[2],
        "name": row[3],
        "opted_out": row[4],
        "last_incoming_at": row[5],
        "last_broadcast_at": row[6],
        "created_at": row[7],
    }


def list_contacts(conn, instance_id) -> list[dict]:
    """
    Gets all contacts for an instance.

    Output: list of contacts row dicts
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, instance_id, remote_jid, name, opted_out, last_incoming_at, last_broadcast_at, created_at
            FROM contacts
            WHERE instance_id = %s
            ORDER BY id ASC
            """,
            (instance_id,),
        )
        rows = cur.fetchall()
    return [_row_to_contact_dict(row) for row in rows]


def update_contact_name(conn, instance_id, contact_id, name) -> bool:
    """
    Updates the name of one contact, scoped to instance_id (the multi-tenant
    guard: a user cannot update a contact outside their own instance).

    Output: True if a row was updated, False otherwise
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE contacts
            SET name = %s
            WHERE id = %s AND instance_id = %s
            RETURNING id
            """,
            (name, contact_id, instance_id),
        )
        row = cur.fetchone()
    return row is not None


def update_contact_opted_out(conn, instance_id, contact_id, opted_out) -> bool:
    """
    Updates the opted_out flag of one contact, scoped to instance_id (the
    multi-tenant guard: a user cannot update a contact outside their own
    instance).

    Output: True if a row was updated, False otherwise
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE contacts
            SET opted_out = %s
            WHERE id = %s AND instance_id = %s
            RETURNING id
            """,
            (opted_out, contact_id, instance_id),
        )
        row = cur.fetchone()
    return row is not None


def upsert_contacts(conn, instance_id: int, contacts: list[dict]) -> None:
    """
    Bulk upserts already-filtered, already-reconciled contacts for an instance.

    Input: contacts as [{"remote_jid": str, "name": str | None}, ...]

    Never overwrites an existing name with an empty/null one (guards against
    the pushName bug on reconciliation), and never touches
    last_incoming_at/last_broadcast_at, which are owned by the webhook.
    """
    if not contacts:
        return
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO contacts (instance_id, remote_jid, name)
            VALUES (%s, %s, %s)
            ON CONFLICT (remote_jid, instance_id)
            DO UPDATE SET name = EXCLUDED.name
            WHERE EXCLUDED.name IS NOT NULL AND EXCLUDED.name != ''
            """,
            [(instance_id, contact["remote_jid"], contact["name"]) for contact in contacts],
        )
