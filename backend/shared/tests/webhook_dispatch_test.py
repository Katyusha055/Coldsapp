from unittest.mock import patch, MagicMock, AsyncMock

import pytest

import backend.shared.webhook_dispatch as webhook_dispatch


@pytest.fixture
def sample_instance():
    return {
        "id": 10,
        "user_id": 1,
        "instance_name": "1_whatsapp",
        "status": "open",
        "notifications_enabled": True,
    }


@pytest.mark.asyncio
async def test_handle_webhook_unknown_instance_skips_processing():
    payload = {"instance": "ghost_instance", "event": "connection.update", "data": {}}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=None), \
         patch('backend.shared.webhook_dispatch.rep.save_event') as mock_save, \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    assert result is None
    mock_save.assert_not_called()
    mock_push.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_webhook_connection_update_routes_to_whatsapp_service(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "connection.update", "data": {"state": "open"}}
    handler_result = {"type": "connection_update", "detail": "open"}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event') as mock_save, \
         patch('backend.shared.webhook_dispatch.whatsapp_service.handle_connection_event', return_value=handler_result) as mock_handle, \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    mock_save.assert_called_once_with(mock_save.call_args.args[0], sample_instance["id"], "connection.update", payload)
    mock_handle.assert_called_once_with(sample_instance, "connection.update", payload)
    assert result == handler_result
    mock_push.assert_awaited_once_with(sample_instance["user_id"], handler_result)


@pytest.mark.asyncio
async def test_handle_webhook_qrcode_updated_routes_to_whatsapp_service(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "qrcode.updated", "data": {}}
    handler_result = {"type": "qr_updated", "detail": "QR code refreshed"}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event'), \
         patch('backend.shared.webhook_dispatch.whatsapp_service.handle_connection_event', return_value=handler_result) as mock_handle, \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    mock_handle.assert_called_once_with(sample_instance, "qrcode.updated", payload)
    assert result == handler_result
    mock_push.assert_awaited_once_with(sample_instance["user_id"], handler_result)


@pytest.mark.asyncio
async def test_handle_webhook_messages_upsert_dispatches_to_both_contacts_and_pendings(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "messages.upsert", "data": {}}
    handler_result = {"type": "new_pending", "id": 1, "remote_jid": "x", "name": "Jane", "message": "hola"}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event'), \
         patch('backend.shared.webhook_dispatch.contacts_service.handle_incoming_message') as mock_contacts, \
         patch('backend.shared.webhook_dispatch.pendings_service.handle_incoming_message', return_value=handler_result) as mock_pendings, \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    mock_contacts.assert_called_once_with(sample_instance, payload)
    mock_pendings.assert_called_once_with(sample_instance, payload)
    assert result == handler_result
    mock_push.assert_awaited_once_with(sample_instance["user_id"], handler_result)


@pytest.mark.asyncio
async def test_handle_webhook_feature_handler_returning_none_is_not_pushed(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "messages.upsert", "data": {}}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event'), \
         patch('backend.shared.webhook_dispatch.contacts_service.handle_incoming_message'), \
         patch('backend.shared.webhook_dispatch.pendings_service.handle_incoming_message', return_value=None), \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    assert result is None
    mock_push.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_webhook_contacts_failure_does_not_block_pendings(sample_instance):
    """
    Integration check that the real @safe_dispatch on contacts_service is
    actually in effect: contacts fails deep inside its own repository call
    (not a mocked-out handle_incoming_message, which would bypass the
    decorator entirely) and pendings must still run to completion.
    """
    payload = {
        "instance": sample_instance["instance_name"], "event": "messages.upsert",
        "data": {"key": {"fromMe": False, "remoteJid": "123@s.whatsapp.net"},
                 "pushName": "Jane", "message": {"conversation": "hola"}},
    }
    created = {"id": 1, "instance_id": sample_instance["id"], "remote_jid": "123@s.whatsapp.net",
               "name": "Jane", "last_message": "hola", "status": "pending"}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event'), \
         patch('backend.contacts.service.connect', return_value=MagicMock()), \
         patch('backend.contacts.service.rep.repair_and_touch', side_effect=RuntimeError("boom")), \
         patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', return_value=None), \
         patch('backend.pendings.service.rep.get_pending_by_remote_jid', return_value=None), \
         patch('backend.pendings.service.rep.create_pending', return_value=created), \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push, \
         patch('backend.shared.error_handlers.logger') as mock_logger:
        result = await webhook_dispatch.handle_webhook(payload)  # must not raise

    assert result["type"] == "new_pending"
    mock_push.assert_awaited_once_with(sample_instance["user_id"], result)
    mock_logger.error.assert_called_once()
    assert mock_logger.error.call_args.args[0].startswith("[webhook:messages.upsert]")
    assert "contacts" in mock_logger.error.call_args.args


@pytest.mark.asyncio
async def test_handle_webhook_pendings_failure_does_not_block_contacts(sample_instance):
    """
    Same check in reverse: pendings fails deep inside its own repository
    call, and contacts must still have run.
    """
    payload = {
        "instance": sample_instance["instance_name"], "event": "messages.upsert",
        "data": {"key": {"fromMe": False, "remoteJid": "123@s.whatsapp.net"},
                 "pushName": "Jane", "message": {"conversation": "hola"}},
    }
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event'), \
         patch('backend.contacts.service.connect', return_value=MagicMock()), \
         patch('backend.contacts.service.rep.repair_and_touch') as mock_repair, \
         patch('backend.pendings.service.connect', return_value=MagicMock()), \
         patch('backend.pendings.service.rep.get_client_by_whatsapp_id', side_effect=RuntimeError("boom")), \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push, \
         patch('backend.shared.error_handlers.logger') as mock_logger:
        result = await webhook_dispatch.handle_webhook(payload)  # must not raise

    mock_repair.assert_called_once()
    assert result is None
    mock_push.assert_not_awaited()
    mock_logger.error.assert_called_once()
    assert mock_logger.error.call_args.args[0].startswith("[webhook:messages.upsert]")
    assert "pendings" in mock_logger.error.call_args.args


@pytest.mark.asyncio
async def test_handle_webhook_unhandled_event_type_returns_none(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "some.other.event", "data": {}}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event') as mock_save, \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    mock_save.assert_called_once()
    assert result is None
    mock_push.assert_not_awaited()
