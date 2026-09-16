from backend.contacts.service import _filter_contacts, _filter_chats, _reconcile


# --- _filter_contacts ---

def test_filter_contacts_keeps_a_real_contact():
    raw = [{"remoteJid": "111@s.whatsapp.net", "pushName": "Alice", "type": "contact"}]

    result = _filter_contacts(raw)

    assert result == [{"remote_jid": "111@s.whatsapp.net", "name": "Alice"}]


def test_filter_contacts_drops_non_contact_types_and_non_net_jids():
    raw = [
        {"remoteJid": "123@g.us", "pushName": "Some Group", "type": "group"},
        {"remoteJid": "222@lid", "pushName": "Unresolved Lid", "type": "contact"},
    ]

    assert _filter_contacts(raw) == []


def test_filter_contacts_drops_the_system_contact():
    """
    Edge case: 0@s.whatsapp.net is WhatsApp's own official/system account. It
    matches type == "contact" and ends with @s.whatsapp.net like a real
    contact would, so it needs its own explicit exclusion.
    """
    raw = [{"remoteJid": "0@s.whatsapp.net", "pushName": "WhatsApp", "type": "contact"}]

    assert _filter_contacts(raw) == []


# --- _filter_chats ---

def test_filter_chats_keeps_a_direct_net_jid():
    raw = [{"remoteJid": "111@s.whatsapp.net", "pushName": "Alice"}]

    result = _filter_chats(raw)

    assert result == [{"remote_jid": "111@s.whatsapp.net", "name": "Alice"}]


def test_filter_chats_drops_bare_lid_and_groups():
    raw = [
        {"remoteJid": "111@lid", "pushName": "No Alt At All"},
        {"remoteJid": "222@g.us", "pushName": "Group Chat"},
    ]

    assert _filter_chats(raw) == []


def test_filter_chats_resolves_lid_via_remote_jid_alt():
    """
    Edge case: an @lid chat with a resolvable remoteJidAlt on its last message
    must resolve to the real number, not be dropped or kept as the raw @lid.
    """
    raw = [
        {
            "remoteJid": "111@lid",
            "pushName": "Alice",
            "lastMessage": {"key": {"remoteJidAlt": "111@s.whatsapp.net"}},
        }
    ]

    result = _filter_chats(raw)

    assert result == [{"remote_jid": "111@s.whatsapp.net", "name": "Alice"}]


# --- _reconcile ---

def test_reconcile_prefers_contacts_name_when_both_sources_have_one():
    contacts = [{"remote_jid": "111@s.whatsapp.net", "name": "Contacts Name"}]
    chats = [{"remote_jid": "111@s.whatsapp.net", "name": "Chats Name"}]

    result = _reconcile(contacts, chats)

    assert result == [{"remote_jid": "111@s.whatsapp.net", "name": "Contacts Name"}]


def test_reconcile_keeps_jids_unique_to_either_source():
    contacts = [{"remote_jid": "111@s.whatsapp.net", "name": "Contacts Only"}]
    chats = [{"remote_jid": "222@s.whatsapp.net", "name": "Chats Only"}]

    result = _reconcile(contacts, chats)

    assert sorted(result, key=lambda c: c["remote_jid"]) == [
        {"remote_jid": "111@s.whatsapp.net", "name": "Contacts Only"},
        {"remote_jid": "222@s.whatsapp.net", "name": "Chats Only"},
    ]


def test_reconcile_never_lets_an_empty_name_overwrite_a_non_empty_one():
    """
    Edge case: whichever side has the non-empty name wins, regardless of
    whether that's the contacts side or the chats side — the pushName bug can
    blank out a name on either source, not just one direction.
    """
    contacts_blank = [{"remote_jid": "111@s.whatsapp.net", "name": None}]
    chats_named = [{"remote_jid": "111@s.whatsapp.net", "name": "Chats Name"}]
    assert _reconcile(contacts_blank, chats_named) == [
        {"remote_jid": "111@s.whatsapp.net", "name": "Chats Name"}
    ]

    contacts_named = [{"remote_jid": "222@s.whatsapp.net", "name": "Contacts Name"}]
    chats_blank = [{"remote_jid": "222@s.whatsapp.net", "name": None}]
    assert _reconcile(contacts_named, chats_blank) == [
        {"remote_jid": "222@s.whatsapp.net", "name": "Contacts Name"}
    ]
