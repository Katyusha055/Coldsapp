from unittest.mock import patch, MagicMock, AsyncMock

import asyncio
import httpx
import pytest
from fastapi import HTTPException

import backend.whatsapp.service as service


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


# --- unknown instance ---

@pytest.mark.asyncio
async def test_process_webhook_unknown_instance_skips_processing():
    payload = {"instance": "ghost_instance", "event": "connection.update", "data": {}}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=None), \
         patch('backend.whatsapp.service.rep.save_event') as mock_save, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    assert result is None
    mock_save.assert_not_called()
    mock_push.assert_not_awaited()


# --- connection.update ---

@pytest.mark.asyncio
async def test_process_webhook_connection_update_updates_status_and_pushes_event(sample_instance):
    payload = {
        "instance": sample_instance["instance_name"],
        "event": "connection.update",
        "data": {"state": "open"},
    }
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event') as mock_save, \
         patch('backend.whatsapp.service.rep.update_instance_status') as mock_update_status, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    mock_save.assert_called_once()
    mock_update_status.assert_called_once_with(mock_save.call_args.args[0], sample_instance["id"], "open")
    assert result == {"type": "connection_update", "detail": "open"}
    mock_push.assert_awaited_once_with(sample_instance["user_id"], result)


# --- qrcode.updated ---

@pytest.mark.asyncio
async def test_process_webhook_qrcode_updated_returns_result(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "qrcode.updated", "data": {}}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    assert result == {"type": "qr_updated", "detail": "QR code refreshed"}
    mock_push.assert_awaited_once_with(sample_instance["user_id"], result)


# --- messages.upsert ---

@pytest.mark.asyncio
async def test_process_webhook_messages_upsert_from_me_is_ignored(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], from_me=True)
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.rep.get_client_by_whatsapp_id') as mock_get_client, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    assert result is None
    mock_get_client.assert_not_called()
    mock_push.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_webhook_messages_upsert_known_client_is_ignored(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"])
    existing_client = {"id": 5, "name": "Jane", "whatsapp_id": "123@s.whatsapp.net"}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.rep.get_client_by_whatsapp_id', return_value=existing_client), \
         patch('backend.whatsapp.service.rep.get_pending_by_remote_jid') as mock_get_pending, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    assert result is None
    mock_get_pending.assert_not_called()
    mock_push.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_webhook_messages_upsert_new_contact_creates_pending(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net", name="Jane", conversation="Hola")
    created = {"id": 99, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
               "name": "Jane", "last_message": "Hola", "status": "pending"}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.whatsapp.service.rep.get_pending_by_remote_jid', return_value=None), \
         patch('backend.whatsapp.service.rep.create_pending', return_value=created) as mock_create, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    mock_create.assert_called_once()
    assert result == {
        "type": "new_pending",
        "id": 99,
        "remote_jid": "123@s.whatsapp.net",
        "name": "Jane",
        "message": "Hola",
    }
    mock_push.assert_awaited_once_with(sample_instance["user_id"], result)


@pytest.mark.asyncio
async def test_process_webhook_messages_upsert_concurrent_insert_falls_back_to_update(sample_instance):
    """
    create_pending returning None means another webhook delivery won the race
    and inserted the row first; the handler should re-fetch it and treat this
    delivery as an update instead of failing.
    """
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net", conversation="Segundo mensaje")
    existing_pending = {"id": 99, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
                         "name": "Jane", "last_message": "Hola", "status": "pending"}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.whatsapp.service.rep.get_pending_by_remote_jid', side_effect=[None, existing_pending]), \
         patch('backend.whatsapp.service.rep.create_pending', return_value=None), \
         patch('backend.whatsapp.service.rep.update_pending_message') as mock_update_message, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    mock_update_message.assert_called_once()
    assert mock_update_message.call_args.args[1] == 99
    assert mock_update_message.call_args.args[2] == "Segundo mensaje"
    assert result == {
        "type": "pending_update",
        "remote_jid": "123@s.whatsapp.net",
        "name": "Jane",
        "message": "Segundo mensaje",
    }
    mock_push.assert_awaited_once_with(sample_instance["user_id"], result)


@pytest.mark.asyncio
async def test_process_webhook_messages_upsert_existing_pending_is_updated(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net", conversation="Otra vez")
    existing_pending = {"id": 42, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
                         "name": "Jane", "last_message": "Hola", "status": "pending"}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.whatsapp.service.rep.get_pending_by_remote_jid', return_value=existing_pending), \
         patch('backend.whatsapp.service.rep.create_pending') as mock_create, \
         patch('backend.whatsapp.service.rep.update_pending_message') as mock_update_message, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    mock_create.assert_not_called()
    mock_update_message.assert_called_once_with(mock_update_message.call_args.args[0], 42, "Otra vez")
    assert result == {
        "type": "pending_update",
        "remote_jid": "123@s.whatsapp.net",
        "name": "Jane",
        "message": "Otra vez",
    }
    mock_push.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_webhook_messages_upsert_converted_pending_is_ignored(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net")
    converted_pending = {"id": 42, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
                          "name": "Jane", "last_message": "Hola", "status": "converted"}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.whatsapp.service.rep.get_pending_by_remote_jid', return_value=converted_pending), \
         patch('backend.whatsapp.service.rep.update_pending_message') as mock_update_message, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    assert result is None
    mock_update_message.assert_not_called()
    mock_push.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_webhook_messages_upsert_extended_text_message_fallback(sample_instance):
    payload = _upsert_payload(sample_instance["instance_name"], remote_jid="123@s.whatsapp.net",
                               extended_text="Mensaje largo con formato")
    created = {"id": 1, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
               "name": "Jane", "last_message": "Mensaje largo con formato", "status": "pending"}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.whatsapp.service.rep.get_pending_by_remote_jid', return_value=None), \
         patch('backend.whatsapp.service.rep.create_pending', return_value=created) as mock_create, \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()):
        result = await service.process_webhook(payload)

    assert mock_create.call_args.args[4] == "Mensaje largo con formato"
    assert result["message"] == "Mensaje largo con formato"


# --- unhandled event ---

@pytest.mark.asyncio
async def test_process_webhook_unhandled_event_type_returns_none(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "some.other.event", "data": {}}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.save_event'), \
         patch('backend.whatsapp.service.push_event', new=AsyncMock()) as mock_push:
        result = await service.process_webhook(payload)

    assert result is None
    mock_push.assert_not_awaited()


# --- get_or_create_instance ---

@pytest.mark.asyncio
async def test_get_or_create_instance_returns_existing_instance_without_calling_evolution(sample_instance):
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_user_id', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.create_evolution_instance', new=AsyncMock()) as mock_create_evo, \
         patch('backend.whatsapp.service.rep.create_instance') as mock_create_instance:
        result = await service.get_or_create_instance(1)

    assert result == sample_instance
    mock_create_evo.assert_not_awaited()
    mock_create_instance.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_instance_creates_evolution_instance_when_missing(sample_instance):
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.get_instance_by_user_id', return_value=None), \
         patch('backend.whatsapp.service.rep.create_evolution_instance', new=AsyncMock()) as mock_create_evo, \
         patch('backend.whatsapp.service.rep.create_instance', return_value=sample_instance) as mock_create_instance:
        result = await service.get_or_create_instance(1)

    mock_create_evo.assert_awaited_once_with("1_whatsapp")
    mock_create_instance.assert_called_once()
    assert mock_create_instance.call_args.args[2] == "1_whatsapp"
    assert result == sample_instance


# --- handle_evo_errors ---

@pytest.mark.asyncio
async def test_handle_evo_errors_passes_through_successful_result():
    @service.handle_evo_errors
    async def ok():
        return {"value": 42}

    assert await ok() == {"value": 42}


@pytest.mark.asyncio
async def test_handle_evo_errors_maps_timeout_to_504():
    @service.handle_evo_errors
    async def times_out():
        raise httpx.TimeoutException("timed out")

    with pytest.raises(HTTPException) as exc_info:
        await times_out()
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_handle_evo_errors_maps_connect_error_to_503():
    @service.handle_evo_errors
    async def unreachable():
        raise httpx.ConnectError("unreachable")

    with pytest.raises(HTTPException) as exc_info:
        await unreachable()
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_handle_evo_errors_propagates_evo_status_and_detail():
    request = httpx.Request("GET", "http://evo.example/instance/connect/1_whatsapp")
    response = httpx.Response(422, request=request, text="invalid instance")
    error = httpx.HTTPStatusError("bad request", request=request, response=response)

    @service.handle_evo_errors
    async def bad_status():
        raise error

    with pytest.raises(HTTPException) as exc_info:
        await bad_status()
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid instance"


# --- register_queue / deregister_queue / push_event ---

def test_register_queue_stores_queue_for_user():
    queue = asyncio.Queue()
    service.register_queue(7, queue)
    try:
        assert service.queues[7] is queue
    finally:
        service.deregister_queue(7)


def test_deregister_queue_removes_user_without_raising_when_absent():
    service.deregister_queue(999)  # never registered
    assert 999 not in service.queues


@pytest.mark.asyncio
async def test_push_event_puts_event_on_registered_users_queue():
    queue = asyncio.Queue()
    service.register_queue(7, queue)
    try:
        await service.push_event(7, {"type": "test"})
        assert queue.get_nowait() == {"type": "test"}
    finally:
        service.deregister_queue(7)


@pytest.mark.asyncio
async def test_push_event_is_a_noop_for_unregistered_user():
    await service.push_event(12345, {"type": "test"})  # should not raise
