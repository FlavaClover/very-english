from uuid import UUID, uuid4

from auth.email_verification import (
    AbstractEmailVerificationService,
    EmailMessage,
    EmailQueue,
)
from services.email_verification import CodeGenerator, EmailVerificationService
from infra.email_verification import EmailVerificationsPg, VerificationCodeHasher


class InMemoryEmailQueue(EmailQueue):
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def enqueue(self, message: EmailMessage) -> None:
        self.messages.append(message)


class FixedCodeGenerator(CodeGenerator):
    def __init__(self, code: str = "123456") -> None:
        self._code = code

    def generate(self) -> str:
        return self._code


class AllowAllEmailVerification(AbstractEmailVerificationService):
    async def send_code(self, email: str) -> None:
        return None

    async def verify_email(self, email: str, code: str) -> UUID:
        return uuid4()

    async def consume_verification(self, verification_id: UUID, email: str) -> None:
        return None


def build_email_verification_service(
    db_connection,
    users,
    queue: InMemoryEmailQueue | None = None,
    code: str = "123456",
    pepper: str = "test-pepper",
) -> EmailVerificationService:
    return EmailVerificationService(
        verifications=EmailVerificationsPg(db_connection),
        users=users,
        queue=queue or InMemoryEmailQueue(),
        code_hasher=VerificationCodeHasher(pepper),
        code_generator=FixedCodeGenerator(code),
        code_ttl_seconds=900,
        verification_ttl_seconds=3600,
    )


async def verify_email_for_tests(
    service: EmailVerificationService,
    email: str,
    code: str = "123456",
) -> UUID:
    await service.send_code(email)
    return await service.verify_email(email, code)


async def register_user_via_api(
    client,
    email: str,
    password: str = "secret-password",
    code: str = "123456",
    first_name: str = "Test",
    last_name: str = "User",
) -> dict:
    send_response = await client.post("/auth/send-code", json={"email": email})
    assert send_response.status_code == 204
    verify_response = await client.post(
        "/auth/verify-email",
        json={"email": email, "code": code},
    )
    assert verify_response.status_code == 200
    verification_id = verify_response.json()["email_verification_id"]
    register_response = await client.post(
        "/auth/register",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
            "email_verification_id": verification_id,
        },
    )
    assert register_response.status_code == 200
    return register_response.json()
