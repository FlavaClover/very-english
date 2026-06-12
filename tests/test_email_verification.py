from uuid import uuid4

import pytest

from auth.exceptions import (
    EmailAlreadyRegisteredError,
    EmailVerificationMismatchError,
    EmailVerificationNotFoundError,
    InvalidVerificationCodeError,
)
from auth.users import UserManager
from auth.models import UserRole
from infra.users import UsersPg
from tests.email_verification_helpers import (
    InMemoryEmailQueue,
    build_email_verification_service,
    verify_email_for_tests,
)
from tests.test_auth import InMemoryMedia, FakeVkIdOAuth
from auth.jwt import JwtIssuer
from auth.passwords import BcryptPasswordHasher


@pytest.fixture
def email_queue() -> InMemoryEmailQueue:
    return InMemoryEmailQueue()


@pytest.fixture
def email_verification_service(db_connection, email_queue):
    return build_email_verification_service(
        db_connection=db_connection,
        users=UsersPg(db_connection),
        queue=email_queue,
        code="654321",
        pepper="test-pepper",
    )


@pytest.fixture
def user_manager_with_verification(
    db_connection,
    email_verification_service,
) -> UserManager:
    return UserManager(
        users=UsersPg(db_connection),
        media=InMemoryMedia(),
        password_hasher=BcryptPasswordHasher(),
        jwt_issuer=JwtIssuer(
            secret_key="test-jwt-secret-key-for-pytest!!",
            expire_minutes=30,
        ),
        vkid_oauth=FakeVkIdOAuth(),
        email_verification_service=email_verification_service,
    )


@pytest.mark.asyncio
async def test_send_code_enqueues_email(email_verification_service, email_queue):
    email = f"new-{uuid4()}@example.com"
    await email_verification_service.send_code(email)

    assert len(email_queue.messages) == 1
    assert email_queue.messages[0].to == email
    assert "654321" in email_queue.messages[0].body_text


@pytest.mark.asyncio
async def test_verify_email_returns_verification_id(email_verification_service):
    email = f"verify-{uuid4()}@example.com"
    verification_id = await verify_email_for_tests(
        email_verification_service,
        email,
        code="654321",
    )

    assert verification_id is not None


@pytest.mark.asyncio
async def test_verify_email_rejects_invalid_code(email_verification_service):
    email = f"invalid-{uuid4()}@example.com"
    await email_verification_service.send_code(email)

    with pytest.raises(InvalidVerificationCodeError):
        await email_verification_service.verify_email(email, "000000")


@pytest.mark.asyncio
async def test_register_requires_matching_verification(
    user_manager_with_verification,
    email_verification_service,
):
    email = f"register-{uuid4()}@example.com"
    verification_id = await verify_email_for_tests(
        email_verification_service,
        email,
        code="654321",
    )

    user = await user_manager_with_verification.register(
        first_name="Test",
        last_name="User",
        email=email,
        password="secret123",
        email_verification_id=verification_id,
    )
    assert user.email == email


@pytest.mark.asyncio
async def test_register_rejects_mismatched_email(
    user_manager_with_verification,
    email_verification_service,
):
    email = f"verified-{uuid4()}@example.com"
    verification_id = await verify_email_for_tests(
        email_verification_service,
        email,
        code="654321",
    )

    with pytest.raises(EmailVerificationMismatchError):
        await user_manager_with_verification.register(
            first_name="Test",
            last_name="User",
            email=f"other-{uuid4()}@example.com",
            password="secret123",
            email_verification_id=verification_id,
        )


@pytest.mark.asyncio
async def test_register_rejects_reused_verification(
    user_manager_with_verification,
    email_verification_service,
):
    email = f"reuse-{uuid4()}@example.com"
    verification_id = await verify_email_for_tests(
        email_verification_service,
        email,
        code="654321",
    )

    await user_manager_with_verification.register(
        first_name="First",
        last_name="User",
        email=email,
        password="secret123",
        email_verification_id=verification_id,
    )

    with pytest.raises(EmailVerificationNotFoundError):
        await user_manager_with_verification.register(
            first_name="Second",
            last_name="User",
            email=email,
            password="secret123",
            email_verification_id=verification_id,
        )


@pytest.mark.asyncio
async def test_send_code_rejects_registered_email(
    db_connection,
    email_verification_service,
    user_manager_with_verification,
):
    email = f"taken-{uuid4()}@example.com"
    verification_id = await verify_email_for_tests(
        email_verification_service,
        email,
        code="654321",
    )
    await user_manager_with_verification.register(
        first_name="Existing",
        last_name="User",
        email=email,
        password="secret123",
        email_verification_id=verification_id,
        role=UserRole.USER,
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        await email_verification_service.send_code(email)
