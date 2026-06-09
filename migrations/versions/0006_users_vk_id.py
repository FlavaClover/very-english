"""users vk_id for VK ID OAuth login

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-05 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет vk_id и разрешает пустой password_hash для OAuth-пользователей."""
    op.execute(
        sa.text(
            """
            ALTER TABLE users
                ADD COLUMN vk_id BIGINT UNIQUE;

            ALTER TABLE users
                ALTER COLUMN password_hash DROP NOT NULL;
            """
        )
    )


def downgrade() -> None:
    """Откатывает vk_id и снова требует password_hash."""
    op.execute(
        sa.text(
            """
            UPDATE users
            SET password_hash = ''
            WHERE password_hash IS NULL;

            ALTER TABLE users
                ALTER COLUMN password_hash SET NOT NULL;

            ALTER TABLE users
                DROP COLUMN IF EXISTS vk_id;
            """
        )
    )
