from unittest.mock import patch, MagicMock, AsyncMock

import httpx
import pytest
from fastapi import HTTPException

import backend.tickets.service as service


@pytest.fixture
def sample_ticket():
    return {
        "id": 1,
        "client_id": 5,
        "title": "Fix display bug",
        "description": "Screen goes black",
        "status": "pending",
        "received_at": "2026-01-01 12:00:00+00:00",
        "ready_at": None,
        "delivered_at": None,
        "created_at": "2026-01-01 12:00:00+00:00",
        "updated_at": "2026-01-01 12:00:00+00:00",
    }


# --- create_ticket ---

def test_create_ticket_happy_path(sample_ticket):
    data = {"client_id": 5, "title": "Fix display bug", "description": "Screen goes black"}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.clients_rep.get_client_by_id', return_value={"id": 5}), \
         patch('backend.tickets.service.rep.create_ticket', return_value=sample_ticket):
        result = service.create_ticket(1, data)
    assert result == sample_ticket


def test_create_ticket_client_not_found():
    data = {"client_id": 999, "title": "Fix display bug", "description": None}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.clients_rep.get_client_by_id', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            service.create_ticket(1, data)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Client not found"


# --- get_tickets ---

def test_get_tickets_happy_path(sample_ticket):
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_tickets', return_value=[sample_ticket]):
        result = service.get_tickets(1)
    assert result == [sample_ticket]


# --- get_ticket_by_id ---

def test_get_ticket_by_id_happy_path(sample_ticket):
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_ticket_by_id', return_value=sample_ticket):
        result = service.get_ticket_by_id(1, 1)
    assert result == sample_ticket


def test_get_ticket_by_id_not_found():
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_ticket_by_id', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            service.get_ticket_by_id(1, 999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Ticket not found"


# --- delete_ticket ---

def test_delete_ticket_happy_path():
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.delete_ticket', return_value={"deleted": True, "id": 1}):
        service.delete_ticket(1, 1)


def test_delete_ticket_not_found():
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.delete_ticket', return_value={"deleted": False, "id": 999}):
        with pytest.raises(HTTPException) as exc_info:
            service.delete_ticket(1, 999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Ticket not found"


# --- update_ticket ---

def test_update_ticket_happy_path(sample_ticket):
    data = {"title": "Updated title", "description": None}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.update_ticket', return_value=sample_ticket):
        result = service.update_ticket(1, 1, data)
    assert result == sample_ticket


def test_update_ticket_no_fields_to_update():
    data = {"title": None, "description": None}
    with pytest.raises(HTTPException) as exc_info:
        service.update_ticket(1, 1, data)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "No fields to update"


def test_update_ticket_no_valid_fields():
    data = {"status": "pending"}
    with pytest.raises(HTTPException) as exc_info:
        service.update_ticket(1, 1, data)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "No valid fields provided for update"


def test_update_ticket_not_found():
    data = {"title": "New title", "description": None}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.update_ticket', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            service.update_ticket(1, 1, data)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Ticket not found"


# --- update_ticket_status ---
@pytest.mark.asyncio
async def test_update_ticket_status_happy_path(sample_ticket):
    updated_ticket = {**sample_ticket, "status": "in_progress"}
    with patch('backend.tickets.service.get_ticket_by_id', return_value=sample_ticket), \
         patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.update_ticket_status', return_value=updated_ticket):
        result = await service.update_ticket_status(1, 1, "in_progress")
    assert result["status"] == "in_progress"

@pytest.mark.asyncio
async def test_update_ticket_status_invalid_transition(sample_ticket):
    with patch('backend.tickets.service.get_ticket_by_id', return_value=sample_ticket):
        with pytest.raises(HTTPException) as exc_info:
            await service.update_ticket_status(1, 1, "delivered")
    assert exc_info.value.status_code == 400
    assert "Cannot transition" in exc_info.value.detail

@pytest.mark.asyncio
async def test_update_ticket_status_not_found(sample_ticket):
    with patch('backend.tickets.service.get_ticket_by_id', return_value=sample_ticket), \
         patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.update_ticket_status', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await service.update_ticket_status(1, 1, "in_progress")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Ticket not found"


@pytest.mark.asyncio
async def test_update_ticket_status_ready_notifies_and_sets_ready_at(sample_ticket):
    updated_ticket = {**sample_ticket, "status": "ready"}
    in_progress_ticket = {**sample_ticket, "status": "in_progress"}
    notification = {"whatsapp_notification_sent": True, "whatsapp_notification_error": None}
    with patch('backend.tickets.service.get_ticket_by_id', return_value=in_progress_ticket), \
         patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.notify_ticket_ready', new=AsyncMock(return_value=notification)) as mock_notify, \
         patch('backend.tickets.service.rep.update_ticket_status', return_value=updated_ticket) as mock_update:
        result = await service.update_ticket_status(1, 1, "ready")

    mock_notify.assert_awaited_once_with(1, in_progress_ticket)
    _, _, _, status_arg, ready_at_arg, delivered_at_arg = mock_update.call_args.args
    assert status_arg == "ready"
    assert ready_at_arg is not None
    assert delivered_at_arg is None
    assert result["whatsapp_notification_sent"] is True
    assert result["whatsapp_notification_error"] is None


@pytest.mark.asyncio
async def test_update_ticket_status_notify_failure_aborts_before_persisting(sample_ticket):
    in_progress_ticket = {**sample_ticket, "status": "in_progress"}
    with patch('backend.tickets.service.get_ticket_by_id', return_value=in_progress_ticket), \
         patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.notify_ticket_ready',
               new=AsyncMock(side_effect=HTTPException(status_code=504, detail="Evolution API timeout"))), \
         patch('backend.tickets.service.rep.update_ticket_status') as mock_update:
        with pytest.raises(HTTPException) as exc_info:
            await service.update_ticket_status(1, 1, "ready")

    assert exc_info.value.status_code == 504
    mock_update.assert_not_called()


# --- notify_ticket_ready ---

def _instance(notifications_enabled=True):
    return {"id": 1, "instance_name": "my-instance", "notifications_enabled": notifications_enabled}


@pytest.mark.asyncio
async def test_notify_ticket_ready_no_instance_skips_notification(sample_ticket):
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_instance_by_user_id', return_value=None):
        result = await service.notify_ticket_ready(1, sample_ticket)
    assert result == {"whatsapp_notification_sent": False, "whatsapp_notification_error": None}


@pytest.mark.asyncio
async def test_notify_ticket_ready_notifications_disabled_skips_notification(sample_ticket):
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_instance_by_user_id', return_value=_instance(notifications_enabled=False)):
        result = await service.notify_ticket_ready(1, sample_ticket)
    assert result == {"whatsapp_notification_sent": False, "whatsapp_notification_error": None}


@pytest.mark.asyncio
async def test_notify_ticket_ready_client_without_phone(sample_ticket):
    client = {"id": 5, "name": "Jane", "phone": None}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_instance_by_user_id', return_value=_instance()), \
         patch('backend.tickets.service.rep.get_client_by_id', return_value=client):
        result = await service.notify_ticket_ready(1, sample_ticket)
    assert result == {"whatsapp_notification_sent": False, "whatsapp_notification_error": "client_has_no_phone"}


@pytest.mark.asyncio
async def test_notify_ticket_ready_happy_path_sends_formatted_number(sample_ticket):
    client = {"id": 5, "name": "Jane", "phone": "0987654321"}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_instance_by_user_id', return_value=_instance()), \
         patch('backend.tickets.service.rep.get_client_by_id', return_value=client), \
         patch('backend.tickets.service.rep.send_whatsapp_message', new=AsyncMock()) as mock_send:
        result = await service.notify_ticket_ready(1, sample_ticket)

    mock_send.assert_awaited_once_with("my-instance", "593987654321", "Hola Jane, tu equipo está listo para retirar.")
    assert result == {"whatsapp_notification_sent": True, "whatsapp_notification_error": None}


@pytest.mark.asyncio
async def test_notify_ticket_ready_evolution_timeout_raises_504(sample_ticket):
    client = {"id": 5, "name": "Jane", "phone": "0987654321"}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_instance_by_user_id', return_value=_instance()), \
         patch('backend.tickets.service.rep.get_client_by_id', return_value=client), \
         patch('backend.tickets.service.rep.send_whatsapp_message',
               new=AsyncMock(side_effect=httpx.TimeoutException("timed out"))):
        with pytest.raises(HTTPException) as exc_info:
            await service.notify_ticket_ready(1, sample_ticket)
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_notify_ticket_ready_evolution_connect_error_raises_503(sample_ticket):
    client = {"id": 5, "name": "Jane", "phone": "0987654321"}
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_instance_by_user_id', return_value=_instance()), \
         patch('backend.tickets.service.rep.get_client_by_id', return_value=client), \
         patch('backend.tickets.service.rep.send_whatsapp_message',
               new=AsyncMock(side_effect=httpx.ConnectError("unreachable"))):
        with pytest.raises(HTTPException) as exc_info:
            await service.notify_ticket_ready(1, sample_ticket)
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_notify_ticket_ready_evolution_http_status_error_propagates_status(sample_ticket):
    client = {"id": 5, "name": "Jane", "phone": "0987654321"}
    request = httpx.Request("POST", "http://evo.example/message/sendText/my-instance")
    response = httpx.Response(422, request=request, text="invalid number")
    error = httpx.HTTPStatusError("bad request", request=request, response=response)
    with patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.get_instance_by_user_id', return_value=_instance()), \
         patch('backend.tickets.service.rep.get_client_by_id', return_value=client), \
         patch('backend.tickets.service.rep.send_whatsapp_message', new=AsyncMock(side_effect=error)):
        with pytest.raises(HTTPException) as exc_info:
            await service.notify_ticket_ready(1, sample_ticket)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid number"


# --- _format_ecuador_phone ---

def test_format_ecuador_phone_strips_leading_zero():
    assert service._format_ecuador_phone("0987654321") == "593987654321"


def test_format_ecuador_phone_without_leading_zero():
    assert service._format_ecuador_phone("987654321") == "593987654321"
