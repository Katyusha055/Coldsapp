"""add contacts table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            instance_id INTEGER NOT NULL,
            remote_jid VARCHAR NOT NULL,
            name VARCHAR,
            opted_out BOOLEAN NOT NULL DEFAULT false,
            last_incoming_at TIMESTAMPTZ,
            last_broadcast_at TIMESTAMPTZ,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE(remote_jid, instance_id),
            CONSTRAINT fk_contacts_instance
                FOREIGN KEY (instance_id)
                REFERENCES whatsapp_instances(id)
                ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS contacts_last_incoming_index ON contacts(instance_id, last_incoming_at);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS contacts_last_incoming_index;")
    op.execute("DROP TABLE IF EXISTS contacts;")
