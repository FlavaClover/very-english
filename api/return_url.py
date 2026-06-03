def validate_return_url(return_url: str, allowed_origins: list[str]) -> None:
    """Проверяет return_url на соответствие разрешённым origin.

    :param return_url: URL возврата после оплаты.
    :param allowed_origins: Список разрешённых origin (CORS).
    :raises ValueError: Если URL не начинается ни с одного origin.
    """
    normalized = return_url.rstrip("/")
    for origin in allowed_origins:
        if origin == "*":
            continue
        candidate = origin.rstrip("/")
        if normalized == candidate or normalized.startswith(f"{candidate}/"):
            return
    raise ValueError("return_url is not allowed")
