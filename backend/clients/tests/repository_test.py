from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from backend.clients import repository as rep

@pytest.fixture
def sample_row():
    return (
        10,
        1,
        "Juan",
        "1234567890",
        "Cliente frecuente",
        datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    )

@pytest.fixture
def mocked_conn_and_cursor():
    conn = MagicMock()
    cursor_cm = conn.cursor.return_value
    cur = MagicMock()
    cursor_cm.__enter__.return_value = cur
    cursor_cm.__exit__.return_value = False
    return conn, cur

def test_row_to_client_dict(sample_row):
    result = rep._row_to_client_dict(sample_row)

    assert result == {
        "id": 10,
        "user_id": 1,
        "name": "Juan",
        "phone": "1234567890",
        "description": "Cliente frecuente",
        "created_at": "2026-01-01 12:00:00+00:00",
    }


def test_get_clients_1(mocked_conn_and_cursor, sample_row):
    conn, cur = mocked_conn_and_cursor
    cur.fetchall.return_value = [sample_row]

    result = rep.get_clients(conn, {"user_id": 1})

    assert result == {
        "items": [
            {
                "id": 10,
                "user_id": 1,
                "name": "Juan",
                "phone": "1234567890",
                "description": "Cliente frecuente",
                "created_at": "2026-01-01 12:00:00+00:00",
            } 
        ]
    }
    cur.execute.assert_called_once()
    query, params = cur.execute.call_args.args
    assert "FROM clients" in query
    assert params == (1,)


def test_create_client_1(mocked_conn_and_cursor, sample_row):
    conn, cur = mocked_conn_and_cursor
    cur.fetchone.return_value = sample_row

    payload = {
        "user_id": 1,
        "name": "Juan",
        "phone": "1234567890",
        "description": "Cliente frecuente",
    }
    result = rep.create_client(conn, payload)

    assert result["id"] == 10
    assert result["user_id"] == 1
    assert result["name"] == "Juan"
    assert result["phone"] == "1234567890"
    assert result["description"] == "Cliente frecuente"
    cur.execute.assert_called_once()


def test_update_client_1(mocked_conn_and_cursor, sample_row):
    conn, cur = mocked_conn_and_cursor
    updated_row = (
        sample_row[0],
        sample_row[1],
        "Juanita",
        sample_row[3],
        "Actualizada",
        sample_row[5],
    )
    cur.fetchone.return_value = updated_row

    data = {"name": "Juanita", "description": "Actualizada"}
    result = rep.update_client(conn, 1, 10, data)

    assert result["id"] == 10
    assert result["user_id"] == 1
    assert result["name"] == "Juanita"
    assert result["description"] == "Actualizada"

    cur.execute.assert_called_once()
    query, values = cur.execute.call_args.args
    assert "UPDATE clients" in query
    assert "name = %s" in query
    assert "description = %s" in query
    assert values == ["Juanita", "Actualizada", 10, 1]


def test_delete_client_happy_path(mocked_conn_and_cursor):
    conn, cur = mocked_conn_and_cursor
    cur.fetchone.return_value = (10,)

    payload = {"id": 10, "user_id": 1}
    result = rep.delete_client(conn, payload)

    assert result == {"deleted": True, "id": 10}
    cur.execute.assert_called_once()
    _, params = cur.execute.call_args.args
    assert params == (10, 1)


def test_get_client_by_phone_1(mocked_conn_and_cursor, sample_row):
    conn, cur = mocked_conn_and_cursor
    cur.fetchone.return_value = sample_row

    result = rep.get_client_by_phone(conn, {"user_id": 1, "phone": "1234567890"})

    assert result["id"] == 10
    assert result["user_id"] == 1
    assert result["phone"] == "1234567890"
    cur.execute.assert_called_once()
    _, params = cur.execute.call_args.args
    assert params == (1, "1234567890")


def test_get_client_by_id_1(mocked_conn_and_cursor, sample_row):
    conn, cur = mocked_conn_and_cursor
    cur.fetchone.return_value = sample_row

    result = rep.get_client_by_id(conn, {"id": 10, "user_id": 1})

    assert result["id"] == 10
    assert result["user_id"] == 1
    assert result["name"] == "Juan"
    cur.execute.assert_called_once()
    _, params = cur.execute.call_args.args
    assert params == (10, 1)

