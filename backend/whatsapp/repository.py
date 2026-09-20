import httpx
from backend.settings import settings

EVO_API_URL = settings.EVO_API_URL
EVO_API_TOKEN = settings.EVO_API_TOKEN
WHATSAPP_WEBHOOK_URL = settings.WHATSAPP_WEBHOOK_URL


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


def create_instance(conn, user_id, instance_name):
    """
    Creates a whatsapp instance row.

    Output dict: WhatsAppInstance-compatible dict
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO whatsapp_instances (user_id, instance_name)
            VALUES (%s, %s)
            RETURNING id, user_id, instance_name, status, created_at, connected_at, notifications_enabled
            """,
            (user_id, instance_name),
        )
        row = cur.fetchone()
    return _row_to_instance_dict(row)


def update_instance_status(conn, instance_id, status, connected_at=None):
    """
    Updates the status (and optionally connected_at) of a whatsapp instance.

    Output dict: WhatsAppInstance-compatible dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE whatsapp_instances
            SET status = %s, connected_at = COALESCE(%s, connected_at)
            WHERE id = %s
            RETURNING id, user_id, instance_name, status, created_at, connected_at, notifications_enabled
            """,
            (status, connected_at, instance_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_instance_dict(row)


def update_notifications_enabled(conn, instance_id, enabled):
    """
    Updates notifications_enabled for a whatsapp instance.

    Output dict: WhatsAppInstance-compatible dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE whatsapp_instances
            SET notifications_enabled = %s
            WHERE id = %s
            RETURNING id, user_id, instance_name, status, created_at, connected_at, notifications_enabled
            """,
            (enabled, instance_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_instance_dict(row)


async def create_evolution_instance(instance_name):
    """
    Calls the Evolution API to create a new whatsapp instance.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{EVO_API_URL}/instance/create",
            headers={"apikey": EVO_API_TOKEN},
            json={
                "instanceName": instance_name,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS",
                "webhook": {
                    "enabled": True,
                    "url": WHATSAPP_WEBHOOK_URL,
                    "events": ["MESSAGES_UPSERT", 'CONNECTION_UPDATE', "QRCODE_UPDATED"],
                },
            },
        )
        response.raise_for_status()
        return response.json()


async def get_evolution_qr(instance_name):
    """
    Calls the Evolution API to fetch a base64 QR code for an instance.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{EVO_API_URL}/instance/connect/{instance_name}",
            headers={"apikey": EVO_API_TOKEN},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("base64")


async def get_evolution_instance_status(instance_name):
    """
    Calls the Evolution API to fetch the connection state for an instance.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{EVO_API_URL}/instance/connectionState/{instance_name}",
            headers={"apikey": EVO_API_TOKEN},
        )
        response.raise_for_status()
        data = response.json()
        instance = data.get("instance", data)
        return instance.get("state") or instance.get("status")
