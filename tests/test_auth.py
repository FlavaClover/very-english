from uuid import uuid4

import pytest

from auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    VkIdAuthError,
)
from auth.jwt import JwtIssuer
from auth.passwords import BcryptPasswordHasher
from auth.users import UserManager
from auth.models import UserRole
from auth.vkid import VkIdTokenResponse, VkIdUserProfile
from infra.users import UsersPg
from tests.conftest import seed_tutor


class FakeVkIdOAuth:
    def __init__(
        self,
        user_id: int = 123456789,
        first_name: str = "Ivan",
        last_name: str = "Petrov",
        email: str | None = "ivan@example.com",
    ) -> None:
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.calls: list[dict[str, str]] = []

    async def exchange_authorization_code(
        self,
        code: str,
        code_verifier: str,
        device_id: str,
        state: str,
    ) -> VkIdTokenResponse:
        self.calls.append(
            {
                "code": code,
                "code_verifier": code_verifier,
                "device_id": device_id,
                "state": state,
            }
        )
        return VkIdTokenResponse(
            access_token="vk-access-token",
            user_id=self.user_id,
        )

    async def get_user_profile(self, access_token: str) -> VkIdUserProfile:
        return VkIdUserProfile(
            user_id=self.user_id,
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
        )


class InMemoryMedia:
    def __init__(self) -> None:
        self.added: list[tuple[str, str]] = []
        self.removed: list[str] = []

    async def add(self, value, name: str) -> None:
        self.added.append((str(value), name))

    async def remove(self, name: str) -> None:
        self.removed.append(name)

    async def url(self, name: str) -> str:
        return f"https://in-memory.test/{name}"


@pytest.fixture
def jwt_issuer() -> JwtIssuer:
    return JwtIssuer(
        secret_key="test-jwt-secret-key-for-pytest!!",
        expire_minutes=30,
    )


@pytest.fixture
def password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


@pytest.fixture
def vkid_oauth() -> FakeVkIdOAuth:
    return FakeVkIdOAuth()


@pytest.fixture
def user_manager(
    db_connection,
    jwt_issuer,
    password_hasher,
    vkid_oauth,
) -> UserManager:
    return UserManager(
        users=UsersPg(db_connection),
        media=InMemoryMedia(),
        password_hasher=password_hasher,
        jwt_issuer=jwt_issuer,
        vkid_oauth=vkid_oauth,
    )


def test_jwt_create_and_decode(jwt_issuer):
    user_id = uuid4()
    tokens = jwt_issuer.create_token_pair(
        user_id=user_id,
        role=UserRole.ADMIN,
        email="admin@example.com",
    )
    access_payload = jwt_issuer.decode_access_token(tokens.access_token)
    refresh_payload = jwt_issuer.decode_refresh_token(tokens.refresh_token)

    assert access_payload["sub"] == str(user_id)
    assert access_payload["role"] == "admin"
    assert access_payload["email"] == "admin@example.com"
    assert refresh_payload["sub"] == str(user_id)


def test_jwt_access_token_rejects_refresh_token(jwt_issuer):
    user_id = uuid4()
    refresh_token = jwt_issuer.create_refresh_token(user_id)

    with pytest.raises(InvalidTokenError):
        jwt_issuer.decode_access_token(refresh_token)


def test_jwt_refresh_tokens_issues_new_pair(jwt_issuer):
    user_id = uuid4()
    tokens = jwt_issuer.create_token_pair(
        user_id=user_id,
        role=UserRole.USER,
        email="user@example.com",
    )

    new_tokens = jwt_issuer.refresh_tokens(
        refresh_token=tokens.refresh_token,
        role=UserRole.USER,
        email="user@example.com",
    )

    assert new_tokens.access_token != tokens.access_token
    assert new_tokens.refresh_token != tokens.refresh_token
    assert jwt_issuer.decode_access_token(new_tokens.access_token)["sub"] == str(
        user_id
    )


def test_jwt_invalid_token_raises(jwt_issuer):
    with pytest.raises(InvalidTokenError):
        jwt_issuer.decode_access_token("not-a-valid-token")


@pytest.mark.asyncio
async def test_register_and_login(user_manager, jwt_issuer):
    user = await user_manager.register(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="secret123",
        role=UserRole.USER,
    )

    assert user.email == "john@example.com"
    assert user.role is UserRole.USER

    logged_in, tokens = await user_manager.login("john@example.com", "secret123")
    assert logged_in.id == user.id

    access_payload = jwt_issuer.decode_access_token(tokens.access_token)
    refresh_payload = jwt_issuer.decode_refresh_token(tokens.refresh_token)
    assert access_payload["sub"] == str(user.id)
    assert refresh_payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_refresh_tokens(user_manager, jwt_issuer):
    await user_manager.register(
        first_name="Refresh",
        last_name="User",
        email="refresh@example.com",
        password="secret123",
    )
    _, tokens = await user_manager.login("refresh@example.com", "secret123")

    new_tokens = await user_manager.refresh(tokens.refresh_token)

    assert new_tokens.access_token != tokens.access_token
    assert new_tokens.refresh_token != tokens.refresh_token
    assert (
        jwt_issuer.decode_access_token(new_tokens.access_token)["email"]
        == "refresh@example.com"
    )


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(user_manager):
    await user_manager.register(
        first_name="First",
        last_name="User",
        email="dup@example.com",
        password="password",
    )

    with pytest.raises(UserAlreadyExistsError):
        await user_manager.register(
            first_name="Second",
            last_name="User",
            email="dup@example.com",
            password="password",
        )


@pytest.mark.asyncio
async def test_login_invalid_password_raises(user_manager):
    await user_manager.register(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        password="correct",
    )

    with pytest.raises(InvalidCredentialsError):
        await user_manager.login("jane@example.com", "wrong")


@pytest.mark.asyncio
async def test_set_photo_uploads_via_media(user_manager, tmp_path):
    user = await user_manager.register(
        first_name="Photo",
        last_name="User",
        email="photo@example.com",
        password="password",
    )
    photo_path = tmp_path / "avatar.png"
    photo_path.write_bytes(b"avatar")

    updated = await user_manager.set_photo(user.id, photo_path, "avatar.png")

    assert updated.photo == "avatar.png"
    media = user_manager._media
    assert len(media.added) == 1
    assert media.added[0][1] == "avatar.png"


@pytest.mark.asyncio
async def test_link_tutor_profile(user_manager, db_connection):
    tutor = await seed_tutor(db_connection)
    user = await user_manager.register(
        first_name="Tutor",
        last_name="Account",
        email="tutor-account@example.com",
        password="password",
        role=UserRole.TUTOR,
    )

    await user_manager.link_tutor_profile(user.id, tutor.id)
    tutor_id = await user_manager.get_tutor_id(user.id)

    assert tutor_id == tutor.id


@pytest.mark.asyncio
async def test_login_vkid_creates_user_and_issues_tokens(
    user_manager,
    jwt_issuer,
    vkid_oauth,
):
    user, tokens = await user_manager.login_vkid(
        code="auth-code",
        state="a" * 32,
        code_verifier="b" * 43,
        device_id="device-1",
    )

    assert user.email == "ivan@example.com"
    assert user.first_name == "Ivan"
    assert user.last_name == "Petrov"
    assert len(vkid_oauth.calls) == 1
    assert vkid_oauth.calls[0]["code"] == "auth-code"

    access_payload = jwt_issuer.decode_access_token(tokens.access_token)
    assert access_payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_login_vkid_returns_existing_user(user_manager, jwt_issuer, vkid_oauth):
    first_user, _ = await user_manager.login_vkid(
        code="auth-code-1",
        state="a" * 32,
        code_verifier="b" * 43,
        device_id="device-1",
    )
    second_user, tokens = await user_manager.login_vkid(
        code="auth-code-2",
        state="c" * 32,
        code_verifier="d" * 43,
        device_id="device-2",
    )

    assert second_user.id == first_user.id
    assert jwt_issuer.decode_access_token(tokens.access_token)["sub"] == str(
        first_user.id
    )


@pytest.mark.asyncio
async def test_login_vkid_rejects_conflicting_email(
    user_manager,
    vkid_oauth,
):
    await user_manager.register(
        first_name="Existing",
        last_name="User",
        email="ivan@example.com",
        password="password",
    )
    vkid_oauth.email = "ivan@example.com"

    with pytest.raises(VkIdAuthError):
        await user_manager.login_vkid(
            code="auth-code",
            state="a" * 32,
            code_verifier="b" * 43,
            device_id="device-1",
        )


@pytest.mark.asyncio
async def test_link_tutor_profile_requires_tutor_role(user_manager, db_connection):
    tutor = await seed_tutor(db_connection)
    user = await user_manager.register(
        first_name="Regular",
        last_name="User",
        email="regular@example.com",
        password="password",
        role=UserRole.USER,
    )

    with pytest.raises(ValueError):
        await user_manager.link_tutor_profile(user.id, tutor.id)
