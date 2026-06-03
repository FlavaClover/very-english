import os


def resolve_http_proxy(cli_proxy: str | None = None) -> str | None:
    """Возвращает URL HTTP(S)-прокси для загрузки медиа.

    Приоритет: аргумент CLI → ``GENERATION_HTTP_PROXY`` → ``HTTPS_PROXY`` →
    ``HTTP_PROXY``.

    :param cli_proxy: Значение флага ``--proxy``, если передан.
    :return: URL прокси или None.
    """
    for value in (
        cli_proxy,
        os.environ.get("GENERATION_HTTP_PROXY"),
        os.environ.get("HTTPS_PROXY"),
        os.environ.get("HTTP_PROXY"),
    ):
        if value and value.strip():
            return value.strip()
    return None


def mask_proxy_url(proxy_url: str) -> str:
    """Маскирует учётные данные в URL прокси для логов.

    :param proxy_url: Исходный URL прокси.
    :return: URL без пароля в открытом виде.
    """
    if "@" not in proxy_url:
        return proxy_url
    scheme_host, host_port = proxy_url.rsplit("@", 1)
    if "://" in scheme_host:
        scheme, _ = scheme_host.split("://", 1)
        return f"{scheme}://***@{host_port}"
    return f"***@{host_port}"
