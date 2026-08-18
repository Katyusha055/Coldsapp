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
