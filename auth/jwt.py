from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from auth.exceptions import InvalidTokenError
from auth.models import UserRole

_ACCESS_TOKEN_TYPE = "access"
_REFRESH_TOKEN_TYPE = "refresh"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


class JwtIssuer:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        expire_minutes: int = 60,
        refresh_expire_days: int = 7,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes
        self._refresh_expire_days = refresh_expire_days

    def create_access_token(
        self,
        user_id: UUID,
        role: UserRole,
        email: str,
    ) -> str:
        """Выпускает JWT access token.

        :param user_id: Идентификатор пользователя.
        :param role: Роль пользователя.
        :param email: Адрес электронной почты.
        :return: Подписанный JWT.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "role": role.value,
            "email": email,
            "type": _ACCESS_TOKEN_TYPE,
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: UUID) -> str:
        """Выпускает JWT refresh token.

        :param user_id: Идентификатор пользователя.
        :return: Подписанный JWT.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "type": _REFRESH_TOKEN_TYPE,
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(days=self._refresh_expire_days),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_token_pair(
        self,
        user_id: UUID,
        role: UserRole,
        email: str,
    ) -> TokenPair:
        """Выпускает пару access и refresh токенов.

        :param user_id: Идентификатор пользователя.
        :param role: Роль пользователя.
        :param email: Адрес электронной почты.
        :return: Пара токенов.
        """
        return TokenPair(
            access_token=self.create_access_token(user_id, role, email),
            refresh_token=self.create_refresh_token(user_id),
        )

    def refresh_tokens(
        self,
        refresh_token: str,
        role: UserRole,
        email: str,
    ) -> TokenPair:
        """Выпускает новую пару токенов по действительному refresh token.

        :param refresh_token: Подписанный refresh JWT.
        :param role: Актуальная роль пользователя.
        :param email: Актуальный адрес электронной почты.
        :return: Новая пара токенов.
        :raises InvalidTokenError: Если refresh token недействителен или просрочен.
        """
        payload = self.decode_refresh_token(refresh_token)
        user_id = UUID(payload["sub"])
        return self.create_token_pair(user_id, role, email)

    def decode_access_token(self, token: str) -> dict[str, str]:
        """Декодирует и проверяет JWT access token.

        :param token: Подписанный JWT.
        :return: Полезная нагрузка с полями ``sub``, ``role``, ``email``.
        :raises InvalidTokenError: Если токен недействителен или просрочен.
        """
        payload = self._decode_token(token)
        if payload.get("type") != _ACCESS_TOKEN_TYPE:
            raise InvalidTokenError

        sub = payload.get("sub")
        role = payload.get("role")
        email = payload.get("email")
        if (
            not isinstance(sub, str)
            or not isinstance(role, str)
            or not isinstance(email, str)
        ):
            raise InvalidTokenError

        return {"sub": sub, "role": role, "email": email}

    def decode_refresh_token(self, token: str) -> dict[str, str]:
        """Декодирует и проверяет JWT refresh token.

        :param token: Подписанный JWT.
        :return: Полезная нагрузка с полем ``sub``.
        :raises InvalidTokenError: Если токен недействителен или просрочен.
        """
        payload = self._decode_token(token)
        if payload.get("type") != _REFRESH_TOKEN_TYPE:
            raise InvalidTokenError

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise InvalidTokenError

        return {"sub": sub}

    def _decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError from exc
