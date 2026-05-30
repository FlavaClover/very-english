from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
from uuid import UUID, uuid4

from auth.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from auth.jwt import JwtIssuer, TokenPair
from auth.models import User, UserRole
from auth.passwords import PasswordHasher
from core.tutors import Media


class Users(ABC):
    @abstractmethod
    async def create(self, user: User, password_hash: str) -> User:
        """Создаёт пользователя с хешем пароля."""

    @abstractmethod
    async def get(self, user_id: UUID) -> User:
        """Возвращает пользователя по идентификатору."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User:
        """Возвращает пользователя по адресу электронной почты."""

    @abstractmethod
    async def get_password_hash(self, user_id: UUID) -> str:
        """Возвращает хеш пароля пользователя."""

    @abstractmethod
    async def update(self, user_id: UUID, user: User) -> User:
        """Обновляет данные пользователя без смены пароля."""

    @abstractmethod
    async def set_photo(self, user_id: UUID, photo: str | None) -> User:
        """Устанавливает или сбрасывает ключ аватара в хранилище."""

    @abstractmethod
    async def is_email_taken(self, email: str) -> bool:
        """Проверяет, занят ли адрес электронной почты."""

    @abstractmethod
    async def link_tutor(self, user_id: UUID, tutor_id: UUID) -> None:
        """Связывает пользователя с профилем тутора."""

    @abstractmethod
    async def get_tutor_id(self, user_id: UUID) -> UUID | None:
        """Возвращает идентификатор профиля тутора, если связь есть."""


class UserManager:
    def __init__(
        self,
        users: Users,
        media: Media,
        password_hasher: PasswordHasher,
        jwt_issuer: JwtIssuer,
    ) -> None:
        self._users = users
        self._media = media
        self._password_hasher = password_hasher
        self._jwt = jwt_issuer

    async def register(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Регистрирует нового пользователя.

        :param first_name: Имя пользователя.
        :param last_name: Фамилия пользователя.
        :param email: Адрес электронной почты.
        :param password: Пароль в открытом виде.
        :param role: Роль пользователя.
        :return: Созданный пользователь без пароля.
        :raises UserAlreadyExistsError: Если email уже занят.
        """
        if await self._users.is_email_taken(email):
            raise UserAlreadyExistsError

        user = User(
            id=uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
        )
        password_hash = self._password_hasher.hash(password)
        return await self._users.create(user, password_hash)

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        """Аутентифицирует пользователя и выпускает пару JWT.

        :param email: Адрес электронной почты.
        :param password: Пароль в открытом виде.
        :return: Пользователь и пара access/refresh токенов.
        :raises InvalidCredentialsError: Если email или пароль неверны.
        """
        try:
            user = await self._users.get_by_email(email)
        except UserNotFoundError:
            raise InvalidCredentialsError from None

        password_hash = await self._users.get_password_hash(user.id)
        if not self._password_hasher.verify(password, password_hash):
            raise InvalidCredentialsError

        tokens = self._jwt.create_token_pair(
            user_id=user.id,
            role=user.role,
            email=user.email,
        )
        return user, tokens

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Обновляет пару токенов по действительному refresh token.

        :param refresh_token: Подписанный refresh JWT.
        :return: Новая пара access/refresh токенов.
        :raises InvalidTokenError: Если refresh token недействителен или просрочен.
        :raises UserNotFoundError: Если пользователь из токена не найден.
        """
        payload = self._jwt.decode_refresh_token(refresh_token)
        user = await self._users.get(UUID(payload["sub"]))
        return self._jwt.refresh_tokens(
            refresh_token=refresh_token,
            role=user.role,
            email=user.email,
        )

    async def get(self, user_id: UUID) -> User:
        """Возвращает пользователя по идентификатору."""
        return await self._users.get(user_id)

    async def update(self, user_id: UUID, user: User) -> User:
        """Обновляет профиль пользователя."""
        return await self._users.update(user_id, user)

    async def set_photo(
        self,
        user_id: UUID,
        path: Path | PathLike | str,
        name: str,
    ) -> User:
        """Загружает аватар через Media и сохраняет ключ в профиле.

        :param user_id: Идентификатор пользователя.
        :param path: Путь к файлу на диске.
        :param name: Ключ объекта в хранилище.
        :return: Обновлённый пользователь.
        """
        user = await self._users.get(user_id)
        if user.photo is not None:
            await self._media.remove(user.photo)

        await self._media.add(path, name)
        return await self._users.set_photo(user_id, name)

    async def remove_photo(self, user_id: UUID) -> User:
        """Удаляет аватар пользователя из хранилища и профиля."""
        user = await self._users.get(user_id)
        if user.photo is not None:
            await self._media.remove(user.photo)

        return await self._users.set_photo(user_id, None)

    async def link_tutor_profile(self, user_id: UUID, tutor_id: UUID) -> None:
        """Связывает пользователя с профилем тутора.

        :param user_id: Идентификатор пользователя.
        :param tutor_id: Идентификатор профиля тутора.
        :raises ValueError: Если у пользователя роль не TUTOR.
        """
        user = await self._users.get(user_id)
        if user.role is not UserRole.TUTOR:
            raise ValueError(
                "Only users with TUTOR role can be linked to a tutor profile"
            )

        await self._users.link_tutor(user_id, tutor_id)

    async def get_tutor_id(self, user_id: UUID) -> UUID | None:
        """Возвращает идентификатор профиля тутора пользователя."""
        return await self._users.get_tutor_id(user_id)
