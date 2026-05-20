from unittest.mock import patch, MagicMock

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

def test_update_ticket_status_happy_path(sample_ticket):
    updated_ticket = {**sample_ticket, "status": "in_progress"}
    with patch('backend.tickets.service.get_ticket_by_id', return_value=sample_ticket), \
         patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.update_ticket_status', return_value=updated_ticket):
        result = service.update_ticket_status(1, 1, "in_progress")
    assert result["status"] == "in_progress"


def test_update_ticket_status_invalid_transition(sample_ticket):
    with patch('backend.tickets.service.get_ticket_by_id', return_value=sample_ticket):
        with pytest.raises(HTTPException) as exc_info:
            service.update_ticket_status(1, 1, "delivered")
    assert exc_info.value.status_code == 400
    assert "Cannot transition" in exc_info.value.detail


def test_update_ticket_status_not_found(sample_ticket):
    with patch('backend.tickets.service.get_ticket_by_id', return_value=sample_ticket), \
         patch('backend.tickets.service.connect', return_value=MagicMock()), \
         patch('backend.tickets.service.rep.update_ticket_status', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            service.update_ticket_status(1, 1, "in_progress")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Ticket not found"
