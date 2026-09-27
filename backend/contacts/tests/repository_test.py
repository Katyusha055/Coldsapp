from datetime import datetime, timezone

from backend.shared.connect import connect
import backend.contacts.repository as rep


def _create_instance(user_id, instance_name="1_whatsapp"):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO whatsapp_instances (user_id, instance_name)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (user_id, instance_name),
            )
            return cur.fetchone()[0]


def _create_contact(instance_id, remote_jid="111@s.whatsapp.net", name=None):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contacts (instance_id, remote_jid, name)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (instance_id, remote_jid, name),
            )
            return cur.fetchone()[0]


def _contact_row(remote_jid, instance_id):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, last_incoming_at FROM contacts WHERE remote_jid = %s AND instance_id = %s",
                (remote_jid, instance_id),
            )
            return cur.fetchone()


# --- repair_and_touch ---

def test_repair_and_touch_fills_null_name_and_updates_timestamp(create_user):
    user = create_user("0999999999")
    instance_id = _create_instance(user["id"])
    _create_contact(instance_id, remote_jid="111@s.whatsapp.net", name=None)
    touched_at = datetime.now(timezone.utc)

    with connect() as conn:
        rep.repair_and_touch(
            conn,
            remote_jid="111@s.whatsapp.net",
            instance_id=instance_id,
            push_name="Jane",
            last_incoming_at=touched_at,
        )

    name, last_incoming_at = _contact_row("111@s.whatsapp.net", instance_id)
    assert name == "Jane"
    assert last_incoming_at is not None


def test_repair_and_touch_never_overwrites_an_already_set_name(create_user):
    user = create_user("0999999999")
    instance_id = _create_instance(user["id"])
    _create_contact(instance_id, remote_jid="111@s.whatsapp.net", name="Original Name")

    with connect() as conn:
        rep.repair_and_touch(
            conn,
            remote_jid="111@s.whatsapp.net",
            instance_id=instance_id,
            push_name="A Different Name",
            last_incoming_at=datetime.now(timezone.utc),
        )

    name, last_incoming_at = _contact_row("111@s.whatsapp.net", instance_id)
    assert name == "Original Name"
    assert last_incoming_at is not None


def test_repair_and_touch_with_no_push_name_only_touches_timestamp(create_user):
    user = create_user("0999999999")
    instance_id = _create_instance(user["id"])
    _create_contact(instance_id, remote_jid="111@s.whatsapp.net", name=None)

    with connect() as conn:
        rep.repair_and_touch(
            conn,
            remote_jid="111@s.whatsapp.net",
            instance_id=instance_id,
            push_name=None,
            last_incoming_at=datetime.now(timezone.utc),
        )

    name, last_incoming_at = _contact_row("111@s.whatsapp.net", instance_id)
    assert name is None
    assert last_incoming_at is not None


def test_repair_and_touch_no_matching_row_is_a_noop(create_user):
    user = create_user("0999999999")
    instance_id = _create_instance(user["id"])
    # No contact created for this remote_jid/instance_id.

    with connect() as conn:
        rep.repair_and_touch(
            conn,
            remote_jid="999@s.whatsapp.net",
            instance_id=instance_id,
            push_name="Nobody",
            last_incoming_at=datetime.now(timezone.utc),
        )
    # No exception raised is the assertion; nothing was created either.
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM contacts WHERE remote_jid = %s AND instance_id = %s",
                ("999@s.whatsapp.net", instance_id),
            )
            assert cur.fetchone()[0] == 0
