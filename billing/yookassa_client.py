import json
import logging

import aiohttp

from billing.subscriptions import (
    PaymentGateway,
    YooKassaPaymentResult,
    YooKassaPaymentStatus,
)

logger = logging.getLogger(__name__)

YOOKASSA_API_BASE = "https://api.yookassa.ru/v3"


class YooKassaApiError(Exception):
    """Ошибка HTTP-ответа API ЮKassa."""


class YooKassaClient(PaymentGateway):
    def __init__(
        self,
        session: aiohttp.ClientSession,
        shop_id: str,
        secret_key: str,
    ) -> None:
        self._session = session
        self._auth = aiohttp.BasicAuth(login=shop_id, password=secret_key)

    async def _request(
        self,
        method: str,
        path: str,
        idempotence_key: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        headers = {"Content-Type": "application/json"}
        if idempotence_key is not None:
            headers["Idempotence-Key"] = idempotence_key

        url = f"{YOOKASSA_API_BASE}{path}"
        async with self._session.request(
            method,
            url,
            json=payload,
            headers=headers,
            auth=self._auth,
        ) as response:
            body_text = await response.text()
            if response.status >= 400:
                raise YooKassaApiError(
                    f"YooKassa API error {response.status}: {body_text}"
                )
            if not body_text:
                return {}
            return json.loads(body_text)

    @staticmethod
    def _parse_payment(data: dict) -> YooKassaPaymentResult:
        confirmation = data.get("confirmation") or {}
        payment_method = data.get("payment_method") or {}
        cancellation = data.get("cancellation_details") or {}
        cancellation_reason = cancellation.get("reason")
        return YooKassaPaymentResult(
            yookassa_payment_id=str(data["id"]),
            status=YooKassaPaymentStatus.from_api_value(str(data.get("status", ""))),
            confirmation_url=confirmation.get("confirmation_url"),
            payment_method_id=payment_method.get("id"),
            cancellation_details=cancellation_reason,
        )

    @staticmethod
    def _amount_payload(amount_rub: int) -> dict:
        return {
            "value": f"{amount_rub:.2f}",
            "currency": "RUB",
        }

    async def create_checkout_payment(
        self,
        amount_rub: int,
        description: str,
        idempotence_key: str,
        return_url: str,
        metadata: dict[str, str],
        save_payment_method: bool = True,
    ) -> YooKassaPaymentResult:
        payload = {
            "amount": self._amount_payload(amount_rub),
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "description": description,
            "save_payment_method": save_payment_method,
            "metadata": metadata,
        }
        data = await self._request(
            "POST",
            "/payments",
            idempotence_key=idempotence_key,
            payload=payload,
        )
        return self._parse_payment(data)

    async def create_autopayment(
        self,
        amount_rub: int,
        description: str,
        idempotence_key: str,
        payment_method_id: str,
        metadata: dict[str, str],
    ) -> YooKassaPaymentResult:
        payload = {
            "amount": self._amount_payload(amount_rub),
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": description,
            "metadata": metadata,
        }
        data = await self._request(
            "POST",
            "/payments",
            idempotence_key=idempotence_key,
            payload=payload,
        )
        return self._parse_payment(data)

    async def get_payment(self, yookassa_payment_id: str) -> YooKassaPaymentResult:
        data = await self._request("GET", f"/payments/{yookassa_payment_id}")
        return self._parse_payment(data)
