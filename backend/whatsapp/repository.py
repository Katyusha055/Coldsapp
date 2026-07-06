import os
import httpx
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()
EVO_API_URL = os.getenv("EVO_API_URL")
EVO_API_TOKEN = os.getenv("EVO_API_TOKEN")
WHATSAPP_WEBHOOK_URL = os.getenv("WHATSAPP_WEBHOOK_URL")


def _row_to_instance_dict(row) -> dict:
    return {
        "id": row[0],
        "user_id": row[1],
        "instance_name": row[2],
        "status": row[3],
        "created_at": row[4],
        "connected_at": row[5],
    }


def get_instance_by_user_id(conn, user_id):
    """
    Gets one whatsapp instance by user_id.

    Output dict: WhatsAppInstance-compatible dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, instance_name, status, created_at, connected_at
            FROM whatsapp_instances
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_instance_dict(row)


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
            RETURNING id, user_id, instance_name, status, created_at, connected_at
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
            RETURNING id, user_id, instance_name, status, created_at, connected_at
            """,
            (status, connected_at, instance_id),
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


def get_instance_by_name(conn, instance_name):
    """
    Gets one whatsapp instance by instance_name.

    Output dict: WhatsAppInstance-compatible dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, instance_name, status, created_at, connected_at
            FROM whatsapp_instances
            WHERE instance_name = %s
            """,
            (instance_name,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_instance_dict(row)


def _row_to_pending_dict(row) -> dict:
    return {
        "id": row[0],
        "instance_id": row[1],
        "remote_jid": row[2],
        "name": row[3],
        "last_message": row[4],
        "last_message_at": row[5],
        "status": row[6],
        "created_at": row[7],
    }


def get_pending_contacts(conn, instance_id):
    """
    Gets all pending contacts for an instance with status 'pending'

    Output: list of wa_pending_contacts row dicts
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, instance_id, remote_jid, name, last_message, last_message_at, status, created_at
            FROM wa_pending_contacts
            WHERE instance_id = %s AND status = 'pending' 
            ORDER BY id ASC
            """,
            (instance_id,),
        )
        rows = cur.fetchall()
    return [_row_to_pending_dict(row) for row in rows]


def get_pending_by_id(conn, pending_id):
    """
    Gets one pending contact by id

    Output dict: wa_pending_contacts row dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, instance_id, remote_jid, name, last_message, last_message_at, status, created_at
            FROM wa_pending_contacts
            WHERE id = %s 
            """,
            (pending_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_pending_dict(row)


def get_pending_by_remote_jid(conn, remote_jid, instance_id):
    """
    Gets one pending contact by remote_jid and instance_id

    Output dict: wa_pending_contacts row dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, instance_id, remote_jid, name, last_message, last_message_at, status, created_at
            FROM wa_pending_contacts
            WHERE remote_jid = %s AND instance_id = %s 
            """,
            (remote_jid, instance_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_pending_dict(row)


def create_pending(conn, instance_id, remote_jid, name, last_message):
    """
    Creates a pending contact row.

    Output dict: wa_pending_contacts row dict (None if a row for this
    remote_jid/instance_id was inserted concurrently by another request)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO wa_pending_contacts (instance_id, remote_jid, name, last_message, last_message_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (remote_jid, instance_id) DO NOTHING
            RETURNING id, instance_id, remote_jid, name, last_message, last_message_at, status, created_at
            """,
            (instance_id, remote_jid, name, last_message),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_pending_dict(row)


def update_pending_message(conn, pending_id, last_message):
    """
    Updates the last message (and timestamp) of a pending contact.

    Output dict: wa_pending_contacts row dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE wa_pending_contacts
            SET last_message = %s, last_message_at = NOW()
            WHERE id = %s
            RETURNING id, instance_id, remote_jid, name, last_message, last_message_at, status, created_at
            """,
            (last_message, pending_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_pending_dict(row)


def update_pending_status(conn, pending_id, status):
    """
    Updates the status of a pending contact.

    Output dict: wa_pending_contacts row dict (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE wa_pending_contacts
            SET status = %s
            WHERE id = %s
            RETURNING id, instance_id, remote_jid, name, last_message, last_message_at, status, created_at
            """,
            (status, pending_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_pending_dict(row)


def delete_pending(conn, pending_id):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM wa_pending_contacts WHERE id = %s RETURNING id",
            (pending_id,)
        )
        row = cur.fetchone()
    return {"deleted": row is not None, "id": pending_id}


def get_client_by_whatsapp_id(conn, remote_jid, user_id):
    """
    Gets one client by whatsapp_id and user.

    Output dict: {"id": int, "name": str, "whatsapp_id": str} (None when not found)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, whatsapp_id
            FROM clients
            WHERE whatsapp_id = %s AND user_id = %s
            LIMIT 1
            """,
            (remote_jid, user_id),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "whatsapp_id": row[2]}


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
