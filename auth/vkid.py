import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)

VK_ID_API_BASE = "https://id.vk.ru"


class VkIdApiError(Exception):
    """Ошибка HTTP-ответа API VK ID."""


@dataclass(frozen=True, slots=True)
class VkIdTokenResponse:
    access_token: str
    user_id: int


@dataclass(frozen=True, slots=True)
class VkIdUserProfile:
    user_id: int
    first_name: str
    last_name: str
    email: str | None = None


class VkIdOAuth(ABC):
    @abstractmethod
    async def exchange_authorization_code(
        self,
        code: str,
        code_verifier: str,
        device_id: str,
        state: str,
    ) -> VkIdTokenResponse:
        """Обменивает authorization code на access token VK ID."""

    @abstractmethod
    async def get_user_profile(self, access_token: str) -> VkIdUserProfile:
        """Возвращает профиль пользователя по access token VK ID."""


class VkIdClient(VkIdOAuth):
    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        redirect_uri: str,
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._redirect_uri = redirect_uri

    async def _post_form(self, path: str, data: dict[str, str]) -> dict:
        url = f"{VK_ID_API_BASE}{path}"
        async with self._session.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as response:
            body_text = await response.text()
            if response.status >= 400:
                raise VkIdApiError(f"VK ID API error {response.status}: {body_text}")
            if not body_text:
                return {}
            return json.loads(body_text)

    async def exchange_authorization_code(
        self,
        code: str,
        code_verifier: str,
        device_id: str,
        state: str,
    ) -> VkIdTokenResponse:
        """Обменивает authorization code на access token VK ID.

        :param code: Код подтверждения из redirect URI.
        :param code_verifier: PKCE code verifier, сгенерированный на клиенте.
        :param device_id: Идентификатор устройства из redirect URI.
        :param state: Строка состояния OAuth.
        :return: Access token и идентификатор пользователя VK ID.
        :raises VkIdApiError: Если VK ID вернул ошибку.
        """
        data = await self._post_form(
            "/oauth2/auth",
            {
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
                "redirect_uri": self._redirect_uri,
                "code": code,
                "client_id": self._client_id,
                "device_id": device_id,
                "state": state,
            },
        )
        if "error" in data:
            raise VkIdApiError(
                f"VK ID token exchange failed: {data.get('error_description', data['error'])}"
            )
        return VkIdTokenResponse(
            access_token=str(data["access_token"]),
            user_id=int(data["user_id"]),
        )

    async def get_user_profile(self, access_token: str) -> VkIdUserProfile:
        """Возвращает профиль пользователя по access token VK ID.

        :param access_token: Access token, полученный при обмене кода.
        :return: Профиль пользователя VK ID.
        :raises VkIdApiError: Если VK ID вернул ошибку.
        """
        data = await self._post_form(
            "/oauth2/user_info",
            {
                "client_id": self._client_id,
                "access_token": access_token,
            },
        )
        if "error" in data:
            raise VkIdApiError(
                f"VK ID user info failed: {data.get('error_description', data['error'])}"
            )
        user = data["user"]
        return VkIdUserProfile(
            user_id=int(user["user_id"]),
            first_name=str(user.get("first_name") or "User"),
            last_name=str(user.get("last_name") or ""),
            email=user.get("email"),
        )
