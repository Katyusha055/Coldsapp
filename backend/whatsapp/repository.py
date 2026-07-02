import os
import httpx
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()
EVO_API_URL = os.getenv("EVO_API_URL")
EVO_API_TOKEN = os.getenv("EVO_API_TOKEN")


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


async def create_evolution_instance(instance_name):
    """
    Calls the Evolution API to create a new whatsapp instance.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{EVO_API_URL}/instance/create",
            headers={"apikey": EVO_API_TOKEN},
            json={"instanceName": instance_name, "qrcode": True, "integration": "WHATSAPP-BAILEYS"},
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
