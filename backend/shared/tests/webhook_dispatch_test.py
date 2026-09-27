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
async def test_handle_webhook_messages_upsert_routes_to_pendings_service(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "messages.upsert", "data": {}}
    handler_result = {"type": "new_pending", "id": 1, "remote_jid": "x", "name": "Jane", "message": "hola"}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event'), \
         patch('backend.shared.webhook_dispatch.pendings_service.handle_incoming_message', return_value=handler_result) as mock_handle, \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    mock_handle.assert_called_once_with(sample_instance, payload)
    assert result == handler_result
    mock_push.assert_awaited_once_with(sample_instance["user_id"], handler_result)


@pytest.mark.asyncio
async def test_handle_webhook_feature_handler_returning_none_is_not_pushed(sample_instance):
    payload = {"instance": sample_instance["instance_name"], "event": "messages.upsert", "data": {}}
    with patch('backend.shared.webhook_dispatch.connect', return_value=MagicMock()), \
         patch('backend.shared.webhook_dispatch.rep.get_instance_by_name', return_value=sample_instance), \
         patch('backend.shared.webhook_dispatch.rep.save_event'), \
         patch('backend.shared.webhook_dispatch.pendings_service.handle_incoming_message', return_value=None), \
         patch('backend.shared.webhook_dispatch.push_event', new=AsyncMock()) as mock_push:
        result = await webhook_dispatch.handle_webhook(payload)

    assert result is None
    mock_push.assert_not_awaited()


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
