"""tutor profile view events for analytics

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-08 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт таблицу событий просмотров профилей туторов для аналитики."""
    op.execute(
        sa.text(
            """
            CREATE TABLE tutor_profile_view_events (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                tutor_id UUID NOT NULL REFERENCES tutors (id) ON DELETE CASCADE,
                viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX tutor_profile_view_events_user_viewed_at_idx
                ON tutor_profile_view_events (user_id, viewed_at DESC);

            CREATE INDEX tutor_profile_view_events_tutor_viewed_at_idx
                ON tutor_profile_view_events (tutor_id, viewed_at DESC);
            """
        )
    )


def downgrade() -> None:
    """Удаляет таблицу событий просмотров профилей туторов."""
    op.execute(
        sa.text(
            """
            DROP INDEX IF EXISTS tutor_profile_view_events_tutor_viewed_at_idx;
            DROP INDEX IF EXISTS tutor_profile_view_events_user_viewed_at_idx;
            DROP TABLE IF EXISTS tutor_profile_view_events;
            """
        )
    )
