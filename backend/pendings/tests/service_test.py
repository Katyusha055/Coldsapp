from unittest.mock import patch, MagicMock, AsyncMock

import pytest

import backend.pendings.service as service


@pytest.fixture
def sample_instance():
    return {
        "id": 10,
        "user_id": 1,
        "instance_name": "1_whatsapp",
        "status": "open",
        "notifications_enabled": True,
    }


def _upsert_payload(instance_name, remote_jid="123@s.whatsapp.net", name="Jane",
                     from_me=False, conversation="Hola", extended_text=None):
    message = {}
    if extended_text is not None:
        message["extendedTextMessage"] = {"text": extended_text}
    else:
        message["conversation"] = conversation

    return {
        "instance": instance_name,
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": from_me, "remoteJid": remote_jid},
            "pushName": name,
            "message": message,
        },
    }


# --- handle_connection_event ---

def test_handle_connection_event_connection_update_updates_status(sample_instance):
    payload = {"data": {"state": "open"}}
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.update_instance_status') as mock_update_status:
        result = service.handle_connection_event(sample_instance, "connection.update", payload)

    mock_update_status.assert_called_once_with(mock_update_status.call_args.args[0], sample_instance["id"], "open")
    assert result == {"type": "connection_update", "detail": "open"}


def test_handle_connection_event_qrcode_updated_returns_result(sample_instance):
    payload = {"data": {}}
    with patch('backend.pendings.service.connect', return_value=MagicMock()):
        result = service.handle_connection_event(sample_instance, "qrcode.updated", payload)

    assert result == {"type": "qr_updated", "detail": "QR code refreshed"}


# --- handle_incoming_message ---

def test_handle_incoming_message_from_me_is_ignored(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], from_me=True)
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id') as mock_get_client:
        result = service.handle_incoming_message(sample_instance, payload)

    assert result is None
    mock_get_client.assert_not_called()


def test_handle_incoming_message_known_client_is_ignored(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"])
    existing_client = {"id": 5, "name": "Jane", "whatsapp_id": "123@s.whatsapp.net"}
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', return_value=existing_client), \
         patch('backend.pendings.service.rep.get_pending_by_remote_jid') as mock_get_pending:
        result = service.handle_incoming_message(sample_instance, payload)

    assert result is None
    mock_get_pending.assert_not_called()


def test_handle_incoming_message_new_contact_creates_pending(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net", name="Jane", conversation="Hola")
    created = {"id": 99, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
               "name": "Jane", "last_message": "Hola", "status": "pending"}
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.pendings.service.rep.get_pending_by_remote_jid', return_value=None), \
         patch('backend.pendings.service.rep.create_pending', return_value=created) as mock_create:
        result = service.handle_incoming_message(sample_instance, payload)

    mock_create.assert_called_once()
    assert result == {
        "type": "new_pending",
        "id": 99,
        "remote_jid": "123@s.whatsapp.net",
        "name": "Jane",
        "message": "Hola",
    }


def test_handle_incoming_message_concurrent_insert_falls_back_to_update(sample_instance):
    """
    create_pending returning None means another webhook delivery won the race
    and inserted the row first; the handler should re-fetch it and treat this
    delivery as an update instead of failing.
    """
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net", conversation="Segundo mensaje")
    existing_pending = {"id": 99, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
                         "name": "Jane", "last_message": "Hola", "status": "pending"}
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.pendings.service.rep.get_pending_by_remote_jid', side_effect=[None, existing_pending]), \
         patch('backend.pendings.service.rep.create_pending', return_value=None), \
         patch('backend.pendings.service.rep.update_pending_message') as mock_update_message:
        result = service.handle_incoming_message(sample_instance, payload)

    mock_update_message.assert_called_once()
    assert mock_update_message.call_args.args[1] == 99
    assert mock_update_message.call_args.args[2] == "Segundo mensaje"
    assert result == {
        "type": "pending_update",
        "remote_jid": "123@s.whatsapp.net",
        "name": "Jane",
        "message": "Segundo mensaje",
    }


def test_handle_incoming_message_existing_pending_is_updated(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net", conversation="Otra vez")
    existing_pending = {"id": 42, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
                         "name": "Jane", "last_message": "Hola", "status": "pending"}
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.pendings.service.rep.get_pending_by_remote_jid', return_value=existing_pending), \
         patch('backend.pendings.service.rep.create_pending') as mock_create, \
         patch('backend.pendings.service.rep.update_pending_message') as mock_update_message:
        result = service.handle_incoming_message(sample_instance, payload)

    mock_create.assert_not_called()
    mock_update_message.assert_called_once_with(mock_update_message.call_args.args[0], 42, "Otra vez")
    assert result == {
        "type": "pending_update",
        "remote_jid": "123@s.whatsapp.net",
        "name": "Jane",
        "message": "Otra vez",
    }


def test_handle_incoming_message_converted_pending_is_ignored(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net")
    converted_pending = {"id": 42, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
                          "name": "Jane", "last_message": "Hola", "status": "converted"}
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.pendings.service.rep.get_pending_by_remote_jid', return_value=converted_pending), \
         patch('backend.pendings.service.rep.update_pending_message') as mock_update_message:
        result = service.handle_incoming_message(sample_instance, payload)

    assert result is None
    mock_update_message.assert_not_called()


def test_handle_incoming_message_extended_text_message_fallback(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net",
                               extended_text="Mensaje largo con formato")
    created = {"id": 1, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
               "name": "Jane", "last_message": "Mensaje largo con formato", "status": "pending"}
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.pendings.service.rep.get_pending_by_remote_jid', return_value=None), \
         patch('backend.pendings.service.rep.create_pending', return_value=created) as mock_create:
        result = service.handle_incoming_message(sample_instance, payload)

    assert mock_create.call_args.args[4] == "Mensaje largo con formato"
    assert result["message"] == "Mensaje largo con formato"


# --- get_or_create_instance ---

@pytest.mark.asyncio
async def test_get_or_create_instance_returns_existing_instance_without_calling_evolution(sample_instance):
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.shared_rep.get_instance_by_user_id', return_value=sample_instance), \
         patch('backend.pendings.service.rep.create_evolution_instance', new=AsyncMock()) as mock_create_evo, \
         patch('backend.pendings.service.rep.create_instance') as mock_create_instance:
        result = await service.get_or_create_instance(1)

    assert result == sample_instance
    mock_create_evo.assert_not_awaited()
    mock_create_instance.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_instance_creates_evolution_instance_when_missing(sample_instance):
    with patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.shared_rep.get_instance_by_user_id', return_value=None), \
         patch('backend.pendings.service.rep.create_evolution_instance', new=AsyncMock()) as mock_create_evo, \
         patch('backend.pendings.service.rep.create_instance', return_value=sample_instance) as mock_create_instance:
        result = await service.get_or_create_instance(1)

    mock_create_evo.assert_awaited_once_with("1_whatsapp")
    mock_create_instance.assert_called_once()
    assert mock_create_instance.call_args.args[2] == "1_whatsapp"
    assert result == sample_instance
