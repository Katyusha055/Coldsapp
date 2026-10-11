from unittest.mock import MagicMock

import pytest

from backend.tickets import repository as rep


@pytest.fixture
def mocked_conn_and_cursor():
    conn = MagicMock()
    cursor_cm = conn.cursor.return_value
    cur = MagicMock()
    cursor_cm.__enter__.return_value = cur
    cursor_cm.__exit__.return_value = False
    return conn, cur


def test_update_ticket_quotes_fields_as_identifiers(mocked_conn_and_cursor):
    conn, cur = mocked_conn_and_cursor
    cur.fetchone.return_value = None

    rep.update_ticket(conn, 1, 10, {"title": "Nuevo", "description": "Desc"})

    query, values = cur.execute.call_args.args
    query = query.as_string()
    assert '"title" = %s' in query
    assert '"description" = %s' in query
    assert "updated_at = NOW()" in query
    assert values == ["Nuevo", "Desc", 10, 1]


def test_update_ticket_rejects_unknown_field(mocked_conn_and_cursor):
    conn, cur = mocked_conn_and_cursor

    with pytest.raises(ValueError):
        rep.update_ticket(conn, 1, 10, {"title": "Nuevo", "user_id": 2})

    cur.execute.assert_not_called()


def test_update_ticket_status_includes_optional_timestamps(mocked_conn_and_cursor):
    conn, cur = mocked_conn_and_cursor
    cur.fetchone.return_value = None

    rep.update_ticket_status(conn, 1, 10, "ready", ready_at="2026-01-01")

    query, values = cur.execute.call_args.args
    query = query.as_string()
    assert "status = %s" in query
    assert "ready_at = %s" in query
    assert "delivered_at" not in query.split("RETURNING")[0]
    assert values == ["ready", "2026-01-01", 10, 1]
