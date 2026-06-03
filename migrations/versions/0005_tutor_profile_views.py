"""tutor profile views history

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт таблицу просмотров профилей туторов пользователями."""
    op.execute(
        sa.text(
            """
            CREATE TABLE tutor_profile_views (
                user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                tutor_id UUID NOT NULL REFERENCES tutors (id) ON DELETE CASCADE,
                viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (user_id, tutor_id)
            );

            CREATE INDEX tutor_profile_views_user_viewed_at_idx
                ON tutor_profile_views (user_id, viewed_at DESC);
            """
        )
    )


def downgrade() -> None:
    """Удаляет таблицу просмотров профилей туторов."""
    op.execute(
        sa.text(
            """
            DROP INDEX IF EXISTS tutor_profile_views_user_viewed_at_idx;
            DROP TABLE IF EXISTS tutor_profile_views;
            """
        )
    )
