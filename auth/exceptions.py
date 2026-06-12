class InvalidCredentialsError(Exception):
    """Неверный email или пароль."""


class UserAlreadyExistsError(Exception):
    """Пользователь с таким email уже существует."""


class UserNotFoundError(Exception):
    """Пользователь с указанным идентификатором или email не найден."""


class InvalidTokenError(Exception):
    """JWT токен недействителен или просрочен."""


class VkIdAuthError(Exception):
    """Ошибка авторизации через VK ID."""


class EmailAlreadyRegisteredError(Exception):
    """Адрес электронной почты уже зарегистрирован."""


class InvalidVerificationCodeError(Exception):
    """Код подтверждения неверен или просрочен."""


class EmailVerificationNotFoundError(Exception):
    """Подтверждение почты не найдено или недоступно для регистрации."""


class EmailVerificationMismatchError(Exception):
    """Email при регистрации не совпадает с подтверждённым."""
