"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-21

This migration mirrors the schema already created by the legacy
schema.py/init_db() functions (clients, tickets, whatsapp). It exists so
Alembic has a starting point in its version history; it is not meant to be
run with `upgrade` against databases that already have these tables (Railway,
local dev) — those get `alembic stamp 0001` instead. Fresh databases (e.g. a
new local setup) run it normally with `alembic upgrade head`.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(20) NOT NULL UNIQUE,
            password_hash VARCHAR(100) NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(100),
            description TEXT,
            whatsapp_id VARCHAR,

            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMPTZ DEFAULT NULL,

            UNIQUE(user_id, whatsapp_id),
            CONSTRAINT fk_clients_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS clients_phone_index ON clients(phone);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_progress', 'ready', 'delivered', 'cancelled')),

            received_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            ready_at TIMESTAMPTZ DEFAULT NULL,
            delivered_at TIMESTAMPTZ DEFAULT NULL,
            deleted_at TIMESTAMPTZ DEFAULT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT fk_tickets_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            CONSTRAINT fk_tickets_client
                FOREIGN KEY (client_id)
                REFERENCES clients(id)
                ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS tickets_client_id_index ON tickets(client_id);")
    op.execute("CREATE INDEX IF NOT EXISTS tickets_status_index ON tickets(status);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_instances (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            instance_name VARCHAR NOT NULL UNIQUE,
            status VARCHAR NOT NULL DEFAULT 'pending',
            notifications_enabled BOOLEAN NOT NULL DEFAULT true,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            connected_at TIMESTAMPTZ,

            CONSTRAINT fk_whatsapp_instances_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS wa_events (
            id SERIAL PRIMARY KEY,
            instance_id INTEGER,
            event_type VARCHAR NOT NULL,
            event_data JSONB NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_wa_events_instance
                FOREIGN KEY (instance_id)
                REFERENCES whatsapp_instances(id)
                ON DELETE CASCADE
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS wa_pending_contacts (
            id SERIAL PRIMARY KEY,
            instance_id INTEGER NOT NULL,
            remote_jid VARCHAR NOT NULL,
            name VARCHAR,
            last_message TEXT,
            last_message_at TIMESTAMPTZ,
            status VARCHAR NOT NULL DEFAULT 'pending',

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE(remote_jid, instance_id),
            CONSTRAINT fk_wa_pending_contacts_instance
                FOREIGN KEY (instance_id)
                REFERENCES whatsapp_instances(id)
                ON DELETE CASCADE
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wa_pending_contacts;")
    op.execute("DROP TABLE IF EXISTS wa_events;")
    op.execute("DROP TABLE IF EXISTS whatsapp_instances;")
    op.execute("DROP TABLE IF EXISTS tickets;")
    op.execute("DROP TABLE IF EXISTS clients;")
    op.execute("DROP TABLE IF EXISTS users;")
