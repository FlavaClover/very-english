import ipaddress

import pytest
from starlette.requests import Request

from billing.yookassa_webhook_ip import (
    YOOKASSA_WEBHOOK_HOSTS,
    YOOKASSA_WEBHOOK_NETWORKS,
    YooKassaWebhookForbiddenError,
    YooKassaWebhookIpValidator,
)


def _request_with_ip(
    address: str | None,
    forwarded_for: str | None = None,
    real_ip: str | None = None,
) -> Request:
    headers = []
    if real_ip is not None:
        headers.append((b"x-real-ip", real_ip.encode()))
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/billing/webhooks/yookassa",
        "headers": headers,
        "client": None if address is None else (address, 0),
    }
    return Request(scope)


@pytest.mark.parametrize(
    "address",
    [
        "77.75.156.11",
        "77.75.156.35",
        "185.71.76.10",
        "185.71.77.5",
        "77.75.153.42",
        "77.75.154.200",
        "2a02:5180:0:1::1",
    ],
)
def test_yookassa_webhook_allows_official_ips(address: str):
    validator = YooKassaWebhookIpValidator()
    assert validator.is_allowed(address) is True


@pytest.mark.parametrize(
    "address",
    [
        "8.8.8.8",
        "127.0.0.1",
        "185.71.76.255",
        "not-an-ip",
    ],
)
def test_yookassa_webhook_rejects_unknown_ips(address: str):
    validator = YooKassaWebhookIpValidator()
    assert validator.is_allowed(address) is False


def test_yookassa_webhook_enforce_uses_x_forwarded_for():
    validator = YooKassaWebhookIpValidator()
    request = _request_with_ip("127.0.0.1", forwarded_for="77.75.156.11")

    assert validator.enforce(request) == "77.75.156.11"


def test_yookassa_webhook_enforce_prefers_x_real_ip():
    validator = YooKassaWebhookIpValidator()
    request = _request_with_ip(
        "127.0.0.1",
        real_ip="77.75.156.11",
        forwarded_for="8.8.8.8",
    )

    assert validator.enforce(request) == "77.75.156.11"


def test_yookassa_webhook_enforce_uses_x_real_ip_from_regru_style_proxy():
    validator = YooKassaWebhookIpValidator()
    request = _request_with_ip("127.0.0.1", real_ip="77.75.156.11")

    assert validator.enforce(request) == "77.75.156.11"


def test_yookassa_webhook_enforce_raises_for_forbidden_ip():
    validator = YooKassaWebhookIpValidator()
    request = _request_with_ip("127.0.0.1")

    with pytest.raises(YooKassaWebhookForbiddenError) as exc_info:
        validator.enforce(request)

    assert exc_info.value.client_ip == "127.0.0.1"


def test_yookassa_webhook_check_can_be_disabled():
    validator = YooKassaWebhookIpValidator(enabled=False)
    request = _request_with_ip("8.8.8.8")

    assert validator.enforce(request) == "8.8.8.8"


def test_yookassa_webhook_networks_cover_documented_ranges():
    assert ipaddress.ip_address("77.75.156.11") in YOOKASSA_WEBHOOK_HOSTS
    assert ipaddress.ip_address("77.75.156.35") in YOOKASSA_WEBHOOK_HOSTS
    assert ipaddress.ip_address("185.71.76.1") in YOOKASSA_WEBHOOK_NETWORKS[0]
