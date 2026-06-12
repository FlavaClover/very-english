import logging
import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from auth.exceptions import (
    EmailAlreadyRegisteredError,
    EmailVerificationMismatchError,
    EmailVerificationNotFoundError,
    InvalidVerificationCodeError,
)
from auth.users import Users
from auth.email_verification import (
    AbstractEmailVerificationService,
    EmailMessage,
    EmailQueue,
    EmailVerificationRepository,
    normalize_email,
)
from infra.email_verification import VerificationCodeHasher

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_SUBJECT = "Код подтверждения Very English"


class CodeGenerator(ABC):
    @abstractmethod
    def generate(self) -> str:
        """Генерирует одноразовый числовой код подтверждения."""


class RandomCodeGenerator(CodeGenerator):
    def __init__(self, length: int = 6) -> None:
        self._length = length
        self._upper_bound = 10**length

    def generate(self) -> str:
        return f"{secrets.randbelow(self._upper_bound):0{self._length}d}"


class EmailVerificationService(AbstractEmailVerificationService):
    def __init__(
        self,
        verifications: EmailVerificationRepository,
        users: Users,
        queue: EmailQueue,
        code_hasher: VerificationCodeHasher,
        code_generator: CodeGenerator,
        code_ttl_seconds: int,
        verification_ttl_seconds: int,
    ) -> None:
        self._verifications = verifications
        self._users = users
        self._queue = queue
        self._code_hasher = code_hasher
        self._code_generator = code_generator
        self._code_ttl_seconds = code_ttl_seconds
        self._verification_ttl_seconds = verification_ttl_seconds

    async def send_code(self, email: str) -> None:
        """Генерирует код, сохраняет его и ставит письмо в очередь.

        :param email: Адрес электронной почты для подтверждения.
        :raises EmailAlreadyRegisteredError: Если email уже зарегистрирован.
        """
        normalized_email = normalize_email(email)
        if await self._users.is_email_taken(normalized_email):
            raise EmailAlreadyRegisteredError

        code = self._code_generator.generate()
        now = datetime.now(UTC)
        code_expires_at = now + timedelta(seconds=self._code_ttl_seconds)
        verification_id = uuid4()
        code_hash = self._code_hasher.hash_code(normalized_email, code)

        await self._verifications.delete_pending_for_email(normalized_email)
        await self._verifications.create_pending(
            verification_id=verification_id,
            email=normalized_email,
            code_hash=code_hash,
            code_expires_at=code_expires_at,
        )
        await self._queue.enqueue(
            EmailMessage(
                to=normalized_email,
                subject=EMAIL_VERIFICATION_SUBJECT,
                body_text=(
                    f"Ваш код подтверждения: {code}\n\n"
                    f"Код действителен {self._code_ttl_seconds // 60} мин."
                ),
            )
        )
        logger.info("Код подтверждения поставлен в очередь для %s", normalized_email)

    async def verify_email(self, email: str, code: str) -> UUID:
        """Проверяет код и возвращает идентификатор подтверждения.

        :param email: Адрес электронной почты.
        :param code: Код из письма.
        :return: Идентификатор подтверждения для регистрации.
        :raises InvalidVerificationCodeError: Если код неверен или просрочен.
        """
        normalized_email = normalize_email(email)
        pending = await self._verifications.get_latest_pending(normalized_email)
        if pending is None:
            raise InvalidVerificationCodeError

        if not self._code_hasher.verify(normalized_email, code, pending.code_hash):
            raise InvalidVerificationCodeError

        now = datetime.now(UTC)
        verification_expires_at = now + timedelta(
            seconds=self._verification_ttl_seconds
        )
        try:
            verified = await self._verifications.mark_verified(
                verification_id=pending.id,
                verified_at=now,
                verification_expires_at=verification_expires_at,
            )
        except LookupError as exc:
            raise InvalidVerificationCodeError from exc

        return verified.id

    async def consume_verification(self, verification_id: UUID, email: str) -> None:
        """Проверяет подтверждение и помечает его использованным.

        :param verification_id: Идентификатор, полученный из ``verify_email``.
        :param email: Email, указанный при регистрации.
        :raises EmailVerificationNotFoundError: Если подтверждение недоступно.
        :raises EmailVerificationMismatchError: Если email не совпадает.
        """
        normalized_email = normalize_email(email)
        try:
            verification = await self._verifications.get_active_verified(
                verification_id
            )
        except LookupError as exc:
            raise EmailVerificationNotFoundError from exc

        if verification.email != normalized_email:
            raise EmailVerificationMismatchError

        now = datetime.now(UTC)
        try:
            await self._verifications.mark_used(verification_id, now)
        except LookupError as exc:
            raise EmailVerificationNotFoundError from exc
