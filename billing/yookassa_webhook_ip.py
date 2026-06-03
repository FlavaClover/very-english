import ipaddress
import logging

from fastapi import Request

logger = logging.getLogger(__name__)

YOOKASSA_WEBHOOK_NETWORKS: tuple[
    ipaddress.IPv4Network | ipaddress.IPv6Network,
    ...,
] = (
    ipaddress.ip_network("185.71.76.0/27"),
    ipaddress.ip_network("185.71.77.0/27"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.154.128/25"),
    ipaddress.ip_network("2a02:5180::/32"),
)

YOOKASSA_WEBHOOK_HOSTS: tuple[
    ipaddress.IPv4Address | ipaddress.IPv6Address,
    ...,
] = (
    ipaddress.ip_address("77.75.156.11"),
    ipaddress.ip_address("77.75.156.35"),
)


class YooKassaWebhookForbiddenError(Exception):
    """Webhook пришёл с IP, не входящего в список ЮKassa."""

    def __init__(self, client_ip: str | None) -> None:
        self.client_ip = client_ip
        super().__init__("YooKassa webhook request from forbidden IP.")


class YooKassaWebhookIpValidator:
    """Проверяет IP-адрес входящего webhook ЮKassa."""

    def __init__(
        self,
        networks: tuple[
            ipaddress.IPv4Network | ipaddress.IPv6Network,
            ...,
        ] = YOOKASSA_WEBHOOK_NETWORKS,
        hosts: tuple[
            ipaddress.IPv4Address | ipaddress.IPv6Address,
            ...,
        ] = YOOKASSA_WEBHOOK_HOSTS,
        enabled: bool = True,
    ) -> None:
        self._networks = networks
        self._hosts = hosts
        self._enabled = enabled

    def resolve_client_ip(self, request: Request) -> str | None:
        """Возвращает IP клиента из proxy-заголовков или scope.

        :param request: HTTP-запрос FastAPI.
        :return: Строка IP или ``None``, если адрес не определён.
        """
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            candidate = real_ip.strip()
            if candidate:
                return candidate

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            candidate = forwarded_for.split(",")[0].strip()
            if candidate:
                return candidate

        if request.client is None:
            return None
        return request.client.host

    def is_allowed(self, address: str | None) -> bool:
        """Проверяет, входит ли IP в список ЮKassa.

        :param address: IP-адрес клиента.
        :return: ``True``, если адрес разрешён или проверка отключена.
        """
        if not self._enabled:
            return True
        if address is None:
            return False
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if ip in self._hosts:
            return True
        return any(ip in network for network in self._networks)

    def enforce(self, request: Request) -> str:
        """Проверяет IP webhook-запроса.

        :param request: HTTP-запрос FastAPI.
        :return: Разрешённый IP клиента.
        :raises YooKassaWebhookForbiddenError: IP не из списка ЮKassa.
        """
        client_ip = self.resolve_client_ip(request)
        if self.is_allowed(client_ip):
            return client_ip or ""
        logger.warning("Rejected YooKassa webhook from IP %s", client_ip)
        raise YooKassaWebhookForbiddenError(client_ip)
