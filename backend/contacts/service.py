import asyncio

from fastapi import HTTPException

import backend.contacts.repository as rep
from backend.database.connect import connect


async def import_contacts(user_id: int) -> dict:
    """
    Fetches contacts and chats from Evolution for the user's WhatsApp
    instance, filters and reconciles them, and upserts the result.

    Output dict: {"imported": int}
    """
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is None:
            raise HTTPException(status_code=404, detail="WhatsApp instance not found")
        if instance["status"] != "open":
            raise HTTPException(status_code=409, detail="WhatsApp instance not connected")

        raw_contacts, raw_chats = await _fetch_sources(instance["instance_name"])

        contacts = _filter_contacts(raw_contacts)
        chats = _filter_chats(raw_chats)
        reconciled = _reconcile(contacts, chats)

        rep.upsert_contacts(conn, instance["id"], reconciled)

    return {"imported": len(reconciled)}


def list_contacts(user_id: int) -> list[dict]:
    """
    Lists all contacts belonging to the user's WhatsApp instance.
    """
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is None:
            raise HTTPException(status_code=404, detail="WhatsApp instance not found")
        return rep.list_contacts(conn, instance["id"])


def update_contact_name(user_id: int, contact_id: int, name: str) -> dict:
    """
    Renames one contact belonging to the user's WhatsApp instance.
    """
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is None:
            raise HTTPException(status_code=404, detail="WhatsApp instance not found")
        updated = rep.update_contact_name(conn, instance["id"], contact_id, name)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"updated": True}


def update_contact_opted_out(user_id: int, contact_id: int, opted_out: bool) -> dict:
    """
    Sets the opted_out flag on one contact belonging to the user's WhatsApp instance.
    """
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is None:
            raise HTTPException(status_code=404, detail="WhatsApp instance not found")
        updated = rep.update_contact_opted_out(conn, instance["id"], contact_id, opted_out)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"updated": True}


async def _fetch_sources(instance_name: str) -> tuple[list, list]:
    """
    Fetches findContacts and findChats from Evolution concurrently.
    """
    raw_contacts, raw_chats = await asyncio.gather(
        rep.find_contacts(instance_name),
        rep.find_chats(instance_name),
    )
    return raw_contacts, raw_chats


def _filter_contacts(raw: list[dict]) -> list[dict]:
    """
    Keeps only real, individual contacts (type == "contact" and a resolved
    @s.whatsapp.net remoteJid). Drops groups and @lid entries.

    Output: [{"remote_jid": str, "name": str | None}, ...]
    """
    filtered = []
    for entry in raw:
        remote_jid = entry.get("remoteJid") or ""
        if entry.get("type") != "contact":
            continue
        if not remote_jid.endswith("@s.whatsapp.net") or remote_jid.startswith("0@"):
            continue
        filtered.append({"remote_jid": remote_jid, "name": entry.get("pushName") or None})
    return filtered


def _filter_chats(raw: list[dict]) -> list[dict]:
    """
    Resolves each chat's real @s.whatsapp.net number: uses remoteJid directly
    when it's already a .net jid, or falls back to lastMessage.key.remoteJidAlt
    when remoteJid is an @lid alias. Chats with no resolvable .net number
    (bare @lid with no alt, @g.us groups) are dropped.

    Name uses top-level pushName only — lastMessage.pushName reflects the
    outgoing sender ("Você"), not the contact, so it's ignored.

    Output: [{"remote_jid": str, "name": str | None}, ...]
    """
    filtered = []
    for chat in raw:
        remote_jid = chat.get("remoteJid") or ""
        resolved_jid = None

        if remote_jid.endswith("@s.whatsapp.net"):
            resolved_jid = remote_jid
        elif remote_jid.endswith("@lid"):
            last_message = chat.get("lastMessage") or {}
            alt_jid = last_message.get("key", {}).get("remoteJidAlt")
            if alt_jid and alt_jid.endswith("@s.whatsapp.net"):
                resolved_jid = alt_jid

        if resolved_jid is None:
            continue

        filtered.append({"remote_jid": resolved_jid, "name": chat.get("pushName") or None})
    return filtered


def _reconcile(contacts: list[dict], chats: list[dict]) -> list[dict]:
    """
    Merges findContacts and findChats results by remote_jid. When a jid
    appears in both: a non-empty name beats an empty/None one, and if both
    are non-empty, findContacts (the canonical directory source) wins.

    Output: [{"remote_jid": str, "name": str | None}, ...], one per remote_jid
    """
    merged: dict[str, str | None] = {}

    for chat in chats:
        merged[chat["remote_jid"]] = chat["name"]

    for contact in contacts:
        remote_jid = contact["remote_jid"]
        if contact["name"] or remote_jid not in merged:
            merged[remote_jid] = contact["name"]

    return [{"remote_jid": remote_jid, "name": name} for remote_jid, name in merged.items()]
