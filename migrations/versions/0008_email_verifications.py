"""email_verifications table for email confirmation flow

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-12 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт таблицу подтверждений email."""
    op.execute(
        sa.text(
            """
            CREATE TABLE email_verifications (
                id UUID PRIMARY KEY,
                email TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                code_expires_at TIMESTAMPTZ NOT NULL,
                verified_at TIMESTAMPTZ,
                verification_expires_at TIMESTAMPTZ,
                used_at TIMESTAMPTZ
            );

            CREATE INDEX idx_email_verifications_email_pending
                ON email_verifications (email, created_at DESC)
                WHERE verified_at IS NULL;
            """
        )
    )


def downgrade() -> None:
    """Удаляет таблицу подтверждений email."""
    op.execute(
        sa.text(
            """
            DROP TABLE IF EXISTS email_verifications;
            """
        )
    )
