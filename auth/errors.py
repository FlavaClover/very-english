class ApplicationError(Exception):
    """Базовое прикладное исключение."""

    code = "application_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AccessDeniedError(ApplicationError):
    """Отказ в доступе (неверный или отсутствующий JWT, неверная роль)."""

    code = "access_denied"
