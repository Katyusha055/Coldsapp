"""add inventory tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # UNIQUE (user_id, id) exists only to be the target of the composite FKs
    # below, so the database itself rejects a code or movement of one user
    # pointing at another user's item.
    op.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(200) NOT NULL,
            low_stock_threshold INTEGER NULL CHECK (low_stock_threshold >= 0),

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ DEFAULT NULL,

            UNIQUE (user_id, id),
            CONSTRAINT fk_items_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS item_codes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            code CHAR(13) NOT NULL CHECK (code ~ '^[0-9]{13}$'),

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE (user_id, code),
            CONSTRAINT fk_item_codes_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_item_codes_item
                FOREIGN KEY (user_id, item_id)
                REFERENCES items (user_id, id)
        );
    """)

    # Append-only ledger: stock is SUM(quantity). The composite FK uses the
    # default NO ACTION (checked at end of statement), not RESTRICT, so a user
    # delete can still cascade through items and movements in one statement.
    op.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity <> 0),
            type VARCHAR(20) NOT NULL
                CHECK (type IN ('initial', 'in', 'out', 'adjustment')),
            note TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT stock_movements_sign_check CHECK (
                (type IN ('in', 'initial') AND quantity > 0) OR
                (type = 'out' AND quantity < 0) OR
                type = 'adjustment'
            ),
            CONSTRAINT fk_stock_movements_user
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_stock_movements_item
                FOREIGN KEY (user_id, item_id)
                REFERENCES items (user_id, id)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS stock_movements_item_index ON stock_movements(user_id, item_id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS stock_movements_item_index;")
    op.execute("DROP TABLE IF EXISTS stock_movements;")
    op.execute("DROP TABLE IF EXISTS item_codes;")
    op.execute("DROP TABLE IF EXISTS items;")
