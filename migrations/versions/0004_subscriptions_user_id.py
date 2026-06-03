"""payments and subscriptions linked to users

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-02 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Переводит payments и подписки с tutor_id на user_id."""
    op.execute(
        sa.text(
            """
            ALTER TABLE payments
                ADD COLUMN user_id UUID REFERENCES users (id) ON DELETE CASCADE;

            UPDATE payments AS p
            SET user_id = ut.user_id
            FROM users_tutor AS ut
            WHERE ut.tutor_id = p.tutor_id;

            ALTER TABLE payments DROP CONSTRAINT payments_tutor_id_fkey;
            DROP INDEX payments_tutor_id_idx;
            ALTER TABLE payments DROP COLUMN tutor_id;
            ALTER TABLE payments ALTER COLUMN user_id SET NOT NULL;
            CREATE INDEX payments_user_id_idx ON payments (user_id);

            ALTER TABLE tutor_subscriptions
                ADD COLUMN user_id UUID REFERENCES users (id) ON DELETE CASCADE;

            UPDATE tutor_subscriptions AS ts
            SET user_id = ut.user_id
            FROM users_tutor AS ut
            WHERE ut.tutor_id = ts.tutor_id;

            ALTER TABLE tutor_subscriptions DROP CONSTRAINT tutor_subscriptions_pkey;
            ALTER TABLE tutor_subscriptions DROP COLUMN tutor_id;
            ALTER TABLE tutor_subscriptions ADD PRIMARY KEY (user_id);
            ALTER TABLE tutor_subscriptions ALTER COLUMN user_id SET NOT NULL;

            ALTER TABLE tutor_subscription_history
                ADD COLUMN user_id UUID REFERENCES users (id) ON DELETE CASCADE;

            UPDATE tutor_subscription_history AS h
            SET user_id = ut.user_id
            FROM users_tutor AS ut
            WHERE ut.tutor_id = h.tutor_id;

            DROP INDEX tutor_subscription_history_tutor_id_idx;
            ALTER TABLE tutor_subscription_history DROP COLUMN tutor_id;
            ALTER TABLE tutor_subscription_history ALTER COLUMN user_id SET NOT NULL;
            CREATE INDEX tutor_subscription_history_user_id_idx
                ON tutor_subscription_history (user_id);
            """
        )
    )


def downgrade() -> None:
    """Возвращает tutor_id в payments и подписках."""
    op.execute(
        sa.text(
            """
            ALTER TABLE tutor_subscription_history
                ADD COLUMN tutor_id UUID REFERENCES tutors (id) ON DELETE CASCADE;

            UPDATE tutor_subscription_history AS h
            SET tutor_id = ut.tutor_id
            FROM users_tutor AS ut
            WHERE ut.user_id = h.user_id;

            DROP INDEX tutor_subscription_history_user_id_idx;
            ALTER TABLE tutor_subscription_history DROP COLUMN user_id;
            CREATE INDEX tutor_subscription_history_tutor_id_idx
                ON tutor_subscription_history (tutor_id);

            ALTER TABLE tutor_subscriptions
                ADD COLUMN tutor_id UUID REFERENCES tutors (id) ON DELETE CASCADE;

            UPDATE tutor_subscriptions AS ts
            SET tutor_id = ut.tutor_id
            FROM users_tutor AS ut
            WHERE ut.user_id = ts.user_id;

            ALTER TABLE tutor_subscriptions DROP CONSTRAINT tutor_subscriptions_pkey;
            ALTER TABLE tutor_subscriptions DROP COLUMN user_id;
            ALTER TABLE tutor_subscriptions ADD PRIMARY KEY (tutor_id);

            ALTER TABLE payments
                ADD COLUMN tutor_id UUID REFERENCES tutors (id) ON DELETE CASCADE;

            UPDATE payments AS p
            SET tutor_id = ut.tutor_id
            FROM users_tutor AS ut
            WHERE ut.user_id = p.user_id;

            DROP INDEX payments_user_id_idx;
            ALTER TABLE payments DROP COLUMN user_id;
            CREATE INDEX payments_tutor_id_idx ON payments (tutor_id);
            """
        )
    )
