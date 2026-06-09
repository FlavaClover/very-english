from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
from uuid import UUID, uuid4

from auth.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    VkIdAuthError,
)
from auth.jwt import JwtIssuer, TokenPair
from auth.models import User, UserRole
from auth.passwords import PasswordHasher
from auth.vkid import VkIdApiError, VkIdOAuth
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

    @abstractmethod
    async def get_by_tutor_id(self, tutor_id: UUID) -> User | None:
        """Возвращает пользователя, связанного с профилем тутора."""

    @abstractmethod
    async def set_autopayment_consent(self, user_id: UUID, consent: bool) -> User:
        """Обновляет согласие пользователя на автоплатежи."""

    @abstractmethod
    async def get_by_vk_id(self, vk_id: int) -> User:
        """Возвращает пользователя по идентификатору VK ID."""

    @abstractmethod
    async def create_vk_user(
        self,
        user: User,
        vk_id: int,
        password_hash: str,
    ) -> User:
        """Создаёт пользователя, привязанного к VK ID."""


class AbstractUserManager(ABC):
    @abstractmethod
    async def register(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        pass

    @abstractmethod
    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        pass

    @abstractmethod
    async def login_vkid(
        self,
        code: str,
        state: str,
        code_verifier: str,
        device_id: str,
    ) -> tuple[User, TokenPair]:
        pass

    @abstractmethod
    async def refresh(self, refresh_token: str) -> TokenPair:
        pass

    @abstractmethod
    async def get(self, user_id: UUID) -> User:
        pass

    @abstractmethod
    async def update(self, user_id: UUID, user: User) -> User:
        pass

    @abstractmethod
    async def set_photo(
        self,
        user_id: UUID,
        path: Path | PathLike | str,
        name: str,
    ) -> User:
        pass

    @abstractmethod
    async def remove_photo(self, user_id: UUID) -> User:
        pass

    @abstractmethod
    async def link_tutor_profile(self, user_id: UUID, tutor_id: UUID) -> None:
        pass

    @abstractmethod
    async def get_tutor_id(self, user_id: UUID) -> UUID | None:
        pass

    @abstractmethod
    async def set_autopayment_consent(self, user_id: UUID, consent: bool) -> User:
        pass


class UserManager(AbstractUserManager):
    def __init__(
        self,
        users: Users,
        media: Media,
        password_hasher: PasswordHasher,
        jwt_issuer: JwtIssuer,
        vkid_oauth: VkIdOAuth,
    ) -> None:
        self._users = users
        self._media = media
        self._password_hasher = password_hasher
        self._jwt = jwt_issuer
        self._vkid_oauth = vkid_oauth

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

    async def login_vkid(
        self,
        code: str,
        state: str,
        code_verifier: str,
        device_id: str,
    ) -> tuple[User, TokenPair]:
        """Аутентифицирует пользователя через VK ID и выпускает пару JWT.

        :param code: Код подтверждения из redirect URI VK ID.
        :param state: Строка состояния OAuth.
        :param code_verifier: PKCE code verifier.
        :param device_id: Идентификатор устройства VK ID.
        :return: Пользователь и пара access/refresh токенов.
        :raises VkIdAuthError: Если VK ID отклонил запрос или профиль недоступен.
        """
        try:
            token_response = await self._vkid_oauth.exchange_authorization_code(
                code=code,
                code_verifier=code_verifier,
                device_id=device_id,
                state=state,
            )
            profile = await self._vkid_oauth.get_user_profile(
                token_response.access_token
            )
        except VkIdApiError as exc:
            raise VkIdAuthError(str(exc)) from exc

        try:
            user = await self._users.get_by_vk_id(profile.user_id)
        except UserNotFoundError:
            email = profile.email or f"{profile.user_id}@vkid.local"
            if await self._users.is_email_taken(email):
                raise VkIdAuthError(
                    "VK ID account cannot be linked: email is already registered"
                ) from None

            last_name = profile.last_name or "—"
            user = User(
                id=uuid4(),
                first_name=profile.first_name,
                last_name=last_name,
                email=email,
                role=UserRole.USER,
            )
            password_hash = self._password_hasher.hash(uuid4().hex)
            user = await self._users.create_vk_user(
                user=user,
                vk_id=profile.user_id,
                password_hash=password_hash,
            )

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

    async def set_autopayment_consent(self, user_id: UUID, consent: bool) -> User:
        """Обновляет согласие тутора на автоплатежи."""
        return await self._users.set_autopayment_consent(user_id, consent)
