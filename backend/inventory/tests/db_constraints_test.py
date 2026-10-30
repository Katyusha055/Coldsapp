"""
Raw SQL against the real DB, bypassing repository and service, to prove each
constraint holds even if the application code had a bug. Every rejection test
first runs a positive control (the same statement with valid data succeeds),
then asserts the exact error and constraint, then checks no row was left.

Each statement runs in its own transaction (`with connect()`), so a rejected
statement rolls back on its own without aborting the rest of the test.
"""

import pytest
from psycopg import errors, sql

from backend.shared.connect import connect

FREE_CODE = "9780201379624"
OTHER_FREE_CODE = "8410076472816"


def _execute(sql, params=()):
    with connect() as conn:
        conn.execute(sql, params)


def _scalar(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchone()[0]


def _rejected(expected_error, sql, params=()):
    with pytest.raises(expected_error) as raised:
        _execute(sql, params)
    return raised.value


def _insert_code(user_id, item_id, code):
    _execute("INSERT INTO item_codes (user_id, item_id, code) VALUES (%s, %s, %s)", (user_id, item_id, code))


def _insert_movement(user_id, item_id, quantity, movement_type):
    _execute(
        "INSERT INTO stock_movements (user_id, item_id, quantity, type) VALUES (%s, %s, %s, %s)",
        (user_id, item_id, quantity, movement_type),
    )


def _new_bare_item(user_id, name):
    with connect() as conn:
        return conn.execute("INSERT INTO items (user_id, name) VALUES (%s, %s) RETURNING id", (user_id, name)).fetchone()[0]


# --- composite foreign keys ---


def test_a_code_cannot_pair_one_user_with_another_users_item(tenants):
    a, b = tenants["a"], tenants["b"]
    _insert_code(a["user_id"], a["item_id"], FREE_CODE)

    error = _rejected(
        errors.ForeignKeyViolation,
        "INSERT INTO item_codes (user_id, item_id, code) VALUES (%s, %s, %s)",
        (a["user_id"], b["item_id"], OTHER_FREE_CODE),
    )

    assert error.diag.constraint_name == "fk_item_codes_item"
    assert _scalar(
        "SELECT COUNT(*) FROM item_codes WHERE user_id = %s AND item_id = %s", (a["user_id"], b["item_id"])
    ) == 0


def test_a_movement_cannot_pair_one_user_with_another_users_item(tenants):
    a, b = tenants["a"], tenants["b"]
    _insert_movement(a["user_id"], a["item_id"], 1, "entry")

    error = _rejected(
        errors.ForeignKeyViolation,
        "INSERT INTO stock_movements (user_id, item_id, quantity, type) VALUES (%s, %s, %s, %s)",
        (a["user_id"], b["item_id"], 1, "entry"),
    )

    assert error.diag.constraint_name == "fk_stock_movements_item"
    assert _scalar(
        "SELECT COUNT(*) FROM stock_movements WHERE user_id = %s AND item_id = %s", (a["user_id"], b["item_id"])
    ) == 0


# --- code uniqueness and format ---


def test_a_user_cannot_hold_the_same_code_twice(tenants):
    a, b = tenants["a"], tenants["b"]
    _insert_code(b["user_id"], b["item_id"], a["code"])

    error = _rejected(
        errors.UniqueViolation,
        "INSERT INTO item_codes (user_id, item_id, code) VALUES (%s, %s, %s)",
        (a["user_id"], a["item_id"], a["code"]),
    )

    assert error.diag.constraint_name == "item_codes_user_id_code_key"
    assert _scalar(
        "SELECT COUNT(*) FROM item_codes WHERE user_id = %s AND code = %s", (a["user_id"], a["code"])
    ) == 1


@pytest.mark.parametrize("bad_code", ["12345", "ABCDEFGHIJKLM", "012345678905"])
def test_a_code_must_be_exactly_13_digits(tenants, bad_code):
    a = tenants["a"]
    _insert_code(a["user_id"], a["item_id"], FREE_CODE)

    error = _rejected(
        errors.CheckViolation,
        "INSERT INTO item_codes (user_id, item_id, code) VALUES (%s, %s, %s)",
        (a["user_id"], a["item_id"], bad_code),
    )

    # CHAR(13) blank-pads shorter values, so they reach the format check.
    assert error.diag.constraint_name == "item_codes_code_check"
    assert _scalar("SELECT COUNT(*) FROM item_codes WHERE user_id = %s", (a["user_id"],)) == 2


def test_a_code_longer_than_13_characters_is_rejected_by_the_column(tenants):
    a = tenants["a"]
    _insert_code(a["user_id"], a["item_id"], FREE_CODE)

    _rejected(
        errors.StringDataRightTruncation,
        "INSERT INTO item_codes (user_id, item_id, code) VALUES (%s, %s, %s)",
        (a["user_id"], a["item_id"], "12345678901234"),
    )

    assert _scalar("SELECT COUNT(*) FROM item_codes WHERE user_id = %s", (a["user_id"],)) == 2


# --- movement quantity, sign and type ---


def test_a_movement_quantity_cannot_be_zero(tenants):
    a = tenants["a"]
    _insert_movement(a["user_id"], a["item_id"], 1, "manual_adjustment")

    error = _rejected(
        errors.CheckViolation,
        "INSERT INTO stock_movements (user_id, item_id, quantity, type) VALUES (%s, %s, %s, %s)",
        (a["user_id"], a["item_id"], 0, "manual_adjustment"),
    )

    assert error.diag.constraint_name == "stock_movements_quantity_check"
    assert _scalar("SELECT COUNT(*) FROM stock_movements WHERE item_id = %s AND quantity = 0", (a["item_id"],)) == 0


@pytest.mark.parametrize(
    ("movement_type", "quantity"),
    [("entry", -1), ("exit", 1), ("initial_adjustment", -1)],
)
def test_a_movement_quantity_must_match_the_sign_of_its_type(tenants, movement_type, quantity):
    a = tenants["a"]
    _insert_movement(a["user_id"], a["item_id"], 1, "entry")
    movements_before = _scalar("SELECT COUNT(*) FROM stock_movements WHERE item_id = %s", (a["item_id"],))

    error = _rejected(
        errors.CheckViolation,
        "INSERT INTO stock_movements (user_id, item_id, quantity, type) VALUES (%s, %s, %s, %s)",
        (a["user_id"], a["item_id"], quantity, movement_type),
    )

    assert error.diag.constraint_name == "stock_movements_sign_check"
    assert _scalar("SELECT COUNT(*) FROM stock_movements WHERE item_id = %s", (a["item_id"],)) == movements_before


@pytest.mark.parametrize("movement_type", ["in", "sale"])
def test_a_movement_type_must_be_one_of_the_four_known_types(tenants, movement_type):
    a = tenants["a"]
    _insert_movement(a["user_id"], a["item_id"], 1, "entry")

    error = _rejected(
        errors.CheckViolation,
        "INSERT INTO stock_movements (user_id, item_id, quantity, type) VALUES (%s, %s, %s, %s)",
        (a["user_id"], a["item_id"], 1, movement_type),
    )

    # Both the type check and the sign check (whose branches list the known
    # types) reject an unknown type; Postgres reports whichever runs first.
    assert error.diag.constraint_name in {"stock_movements_type_check", "stock_movements_sign_check"}
    assert _scalar("SELECT COUNT(*) FROM stock_movements WHERE type = %s", (movement_type,)) == 0


# --- item threshold ---


def test_a_low_stock_threshold_cannot_be_negative(tenants):
    a = tenants["a"]
    _execute("INSERT INTO items (user_id, name, low_stock_threshold) VALUES (%s, 'Control', 0)", (a["user_id"],))

    error = _rejected(
        errors.CheckViolation,
        "INSERT INTO items (user_id, name, low_stock_threshold) VALUES (%s, 'Negativo', -1)",
        (a["user_id"],),
    )

    assert error.diag.constraint_name == "items_low_stock_threshold_check"
    assert _scalar("SELECT COUNT(*) FROM items WHERE name = 'Negativo'") == 0


# --- deleting items and users ---


@pytest.mark.parametrize("attached", ["movement", "code"])
def test_an_item_with_a_movement_or_a_code_cannot_be_deleted(tenants, attached):
    a = tenants["a"]
    bare_item = _new_bare_item(a["user_id"], "Sin nada")
    _execute("DELETE FROM items WHERE id = %s", (bare_item,))

    item_id = _new_bare_item(a["user_id"], "Con algo")
    if attached == "movement":
        _insert_movement(a["user_id"], item_id, 1, "entry")
        expected_constraint = "fk_stock_movements_item"
    else:
        _insert_code(a["user_id"], item_id, FREE_CODE)
        expected_constraint = "fk_item_codes_item"

    error = _rejected(errors.ForeignKeyViolation, "DELETE FROM items WHERE id = %s", (item_id,))

    assert error.diag.constraint_name == expected_constraint
    assert _scalar("SELECT COUNT(*) FROM items WHERE id = %s", (item_id,)) == 1
    assert _scalar(
        "SELECT (SELECT COUNT(*) FROM stock_movements WHERE item_id = %s) + (SELECT COUNT(*) FROM item_codes WHERE item_id = %s)",
        (item_id, item_id),
    ) == 1


def test_deleting_a_user_cascades_through_items_codes_and_movements(tenants):
    a, b = tenants["a"], tenants["b"]

    _execute("DELETE FROM users WHERE id = %s", (a["user_id"],))

    for table in ("items", "item_codes", "stock_movements"):
        count_for_user = sql.SQL("SELECT COUNT(*) FROM {} WHERE user_id = %s").format(sql.Identifier(table))
        assert _scalar(count_for_user, (a["user_id"],)) == 0
        assert _scalar(count_for_user, (b["user_id"],)) == 1
