from unittest.mock import patch, MagicMock, AsyncMock

import pytest

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


# --- handle_connection_event ---

def test_handle_connection_event_connection_update_updates_status(sample_instance):
    payload = {"data": {"state": "open"}}
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.rep.update_instance_status') as mock_update_status:
        result = service.handle_connection_event(sample_instance, "connection.update", payload)

    mock_update_status.assert_called_once_with(mock_update_status.call_args.args[0], sample_instance["id"], "open")
    assert result == {"type": "connection_update", "detail": "open"}


def test_handle_connection_event_qrcode_updated_returns_result_without_touching_db(sample_instance):
    payload = {"data": {}}
    with patch('backend.whatsapp.service.connect') as mock_connect:
        result = service.handle_connection_event(sample_instance, "qrcode.updated", payload)

    assert result == {"type": "qr_updated", "detail": "QR code refreshed"}
    mock_connect.assert_not_called()


def test_handle_connection_event_unexpected_event_returns_none(sample_instance):
    payload = {"data": {}}
    with patch('backend.whatsapp.service.connect') as mock_connect:
        result = service.handle_connection_event(sample_instance, "some.other.event", payload)

    assert result is None
    mock_connect.assert_not_called()


# --- get_or_create_instance ---

@pytest.mark.asyncio
async def test_get_or_create_instance_returns_existing_instance_without_calling_evolution(sample_instance):
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.shared_rep.get_instance_by_user_id', return_value=sample_instance), \
         patch('backend.whatsapp.service.rep.create_evolution_instance', new=AsyncMock()) as mock_create_evo, \
         patch('backend.whatsapp.service.rep.create_instance') as mock_create_instance:
        result = await service.get_or_create_instance(1)

    assert result == sample_instance
    mock_create_evo.assert_not_awaited()
    mock_create_instance.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_instance_creates_evolution_instance_when_missing(sample_instance):
    with patch('backend.whatsapp.service.connect', return_value=MagicMock()), \
         patch('backend.whatsapp.service.shared_rep.get_instance_by_user_id', return_value=None), \
         patch('backend.whatsapp.service.rep.create_evolution_instance', new=AsyncMock()) as mock_create_evo, \
         patch('backend.whatsapp.service.rep.create_instance', return_value=sample_instance) as mock_create_instance:
        result = await service.get_or_create_instance(1)

    mock_create_evo.assert_awaited_once_with("1_whatsapp")
    mock_create_instance.assert_called_once()
    assert mock_create_instance.call_args.args[2] == "1_whatsapp"
    assert result == sample_instance
