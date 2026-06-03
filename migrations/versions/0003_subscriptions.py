"""subscription plans, payments, tutor subscriptions

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт схему подписок, платежей и флаг автоплатежей."""
    op.execute(
        sa.text(
            """
            CREATE TYPE subscription_plan AS ENUM ('base', 'pro');

            CREATE TYPE subscription_status AS ENUM (
                'active',
                'past_due',
                'expired',
                'canceled'
            );

            CREATE TYPE payment_event_type AS ENUM (
                'initial',
                'renewal',
                'upgrade'
            );

            CREATE TYPE payment_status AS ENUM (
                'pending',
                'succeeded',
                'canceled'
            );

            CREATE TABLE subscription_plans (
                id subscription_plan PRIMARY KEY,
                price_rub INTEGER NOT NULL CHECK (price_rub > 0),
                billing_interval TEXT NOT NULL DEFAULT 'month'
            );

            INSERT INTO subscription_plans (id, price_rub, billing_interval)
            VALUES
                ('base', 990, 'month'),
                ('pro', 1990, 'month');

            ALTER TABLE users
                ADD COLUMN autopayment_consent BOOLEAN NOT NULL DEFAULT FALSE;

            CREATE TABLE payments (
                id UUID PRIMARY KEY,
                tutor_id UUID NOT NULL REFERENCES tutors (id) ON DELETE CASCADE,
                plan_id subscription_plan NOT NULL REFERENCES subscription_plans (id),
                event_type payment_event_type NOT NULL,
                amount_rub INTEGER NOT NULL CHECK (amount_rub > 0),
                status payment_status NOT NULL DEFAULT 'pending',
                yookassa_payment_id TEXT UNIQUE,
                idempotence_key TEXT NOT NULL UNIQUE,
                yookassa_payment_method_id TEXT,
                cancellation_details TEXT,
                paid_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX payments_tutor_id_idx ON payments (tutor_id);
            CREATE INDEX payments_status_pending_idx ON payments (status)
                WHERE status = 'pending';

            CREATE TABLE tutor_subscriptions (
                tutor_id UUID PRIMARY KEY REFERENCES tutors (id) ON DELETE CASCADE,
                plan_id subscription_plan NOT NULL REFERENCES subscription_plans (id),
                status subscription_status NOT NULL,
                period_start TIMESTAMPTZ NOT NULL,
                period_end TIMESTAMPTZ NOT NULL,
                paid_at TIMESTAMPTZ NOT NULL,
                yookassa_payment_method_id TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE tutor_subscription_history (
                id UUID PRIMARY KEY,
                tutor_id UUID NOT NULL REFERENCES tutors (id) ON DELETE CASCADE,
                payment_id UUID NOT NULL UNIQUE REFERENCES payments (id) ON DELETE CASCADE,
                plan_id subscription_plan NOT NULL REFERENCES subscription_plans (id),
                event_type payment_event_type NOT NULL,
                period_start TIMESTAMPTZ NOT NULL,
                period_end TIMESTAMPTZ NOT NULL,
                paid_at TIMESTAMPTZ NOT NULL
            );

            CREATE INDEX tutor_subscription_history_tutor_id_idx
                ON tutor_subscription_history (tutor_id);
            """
        )
    )


def downgrade() -> None:
    """Откатывает схему подписок и платежей."""
    op.execute(
        sa.text(
            """
            DROP TABLE IF EXISTS tutor_subscription_history;
            DROP TABLE IF EXISTS tutor_subscriptions;
            DROP TABLE IF EXISTS payments;
            ALTER TABLE users DROP COLUMN IF EXISTS autopayment_consent;
            DROP TABLE IF EXISTS subscription_plans;
            DROP TYPE IF EXISTS payment_status;
            DROP TYPE IF EXISTS payment_event_type;
            DROP TYPE IF EXISTS subscription_status;
            DROP TYPE IF EXISTS subscription_plan;
            """
        )
    )
