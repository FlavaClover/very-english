from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


def normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass(frozen=True, slots=True)
class EmailVerification:
    """Запись подтверждения адреса электронной почты."""

    id: UUID
    email: str
    code_hash: str
    created_at: datetime
    code_expires_at: datetime
    verified_at: datetime | None
    verification_expires_at: datetime | None
    used_at: datetime | None


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """Сообщение для асинхронной отправки по электронной почте."""

    to: str
    subject: str
    body_text: str


class EmailVerificationRepository(ABC):
    @abstractmethod
    async def create_pending(
        self,
        verification_id: UUID,
        email: str,
        code_hash: str,
        code_expires_at: datetime,
    ) -> EmailVerification:
        """Создаёт новую запись с кодом подтверждения."""

    @abstractmethod
    async def delete_pending_for_email(self, email: str) -> None:
        """Удаляет неподтверждённые записи для указанного адреса."""

    @abstractmethod
    async def get_latest_pending(self, email: str) -> EmailVerification | None:
        """Возвращает последнюю неподтверждённую запись, если код ещё действителен."""

    @abstractmethod
    async def mark_verified(
        self,
        verification_id: UUID,
        verified_at: datetime,
        verification_expires_at: datetime,
    ) -> EmailVerification:
        """Помечает запись как подтверждённую."""

    @abstractmethod
    async def get_active_verified(self, verification_id: UUID) -> EmailVerification:
        """Возвращает подтверждённую и неиспользованную запись."""

    @abstractmethod
    async def mark_used(self, verification_id: UUID, used_at: datetime) -> None:
        """Помечает подтверждение как использованное при регистрации."""


class EmailQueue(ABC):
    @abstractmethod
    async def enqueue(self, message: EmailMessage) -> None:
        """Ставит письмо в очередь на отправку."""


class EmailSender(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> None:
        """Отправляет письмо через транспорт (SMTP и т.п.)."""


class AbstractEmailVerificationService(ABC):
    @abstractmethod
    async def send_code(self, email: str) -> None:
        pass

    @abstractmethod
    async def verify_email(self, email: str, code: str) -> UUID:
        pass

    @abstractmethod
    async def consume_verification(self, verification_id: UUID, email: str) -> None:
        pass
