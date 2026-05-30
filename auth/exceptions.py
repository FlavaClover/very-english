class InvalidCredentialsError(Exception):
    """Неверный email или пароль."""


class UserAlreadyExistsError(Exception):
    """Пользователь с таким email уже существует."""


class UserNotFoundError(Exception):
    """Пользователь с указанным идентификатором или email не найден."""


class InvalidTokenError(Exception):
    """JWT токен недействителен или просрочен."""
