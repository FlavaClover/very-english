from datetime import UTC, datetime, timedelta

from services.subscription import SubscriptionService


def test_calculate_upgrade_amount_rub_mid_period():
    period_start = datetime(2026, 1, 1, tzinfo=UTC)
    period_end = datetime(2026, 2, 1, tzinfo=UTC)
    now = datetime(2026, 1, 16, tzinfo=UTC)

    amount = SubscriptionService._calculate_upgrade_amount_rub(
        base_price_rub=990,
        pro_price_rub=1990,
        period_start=period_start,
        period_end=period_end,
        now=now,
    )
    assert amount > 0
    assert amount < 1000


def test_calculate_upgrade_amount_rub_after_period():
    period_start = datetime(2026, 1, 1, tzinfo=UTC)
    period_end = datetime(2026, 2, 1, tzinfo=UTC)
    now = period_end + timedelta(days=1)

    amount = SubscriptionService._calculate_upgrade_amount_rub(
        base_price_rub=990,
        pro_price_rub=1990,
        period_start=period_start,
        period_end=period_end,
        now=now,
    )
    assert amount == 0


def test_add_billing_month():
    start = datetime(2026, 1, 31, 12, 0, tzinfo=UTC)
    end = SubscriptionService._add_billing_month(start)
    assert end.month == 2
    assert end.day == 28
