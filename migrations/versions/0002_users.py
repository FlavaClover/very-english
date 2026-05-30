"""users and users_tutor tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт таблицы пользователей и связь с профилями туторов."""
    op.execute(
        sa.text(
            """
            CREATE TYPE user_role AS ENUM (
                'admin',
                'tutor',
                'user'
            );

            CREATE TABLE users (
                id UUID PRIMARY KEY,
                photo TEXT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role user_role NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE users_tutor (
                user_id UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
                tutor_id UUID NOT NULL UNIQUE REFERENCES tutors (id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )


def downgrade() -> None:
    """Откатывает таблицы пользователей."""
    op.execute(
        sa.text(
            """
            DROP TABLE IF EXISTS users_tutor;
            DROP TABLE IF EXISTS users;
            DROP TYPE IF EXISTS user_role;
            """
        )
    )
