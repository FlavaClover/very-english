import hashlib
import json
import logging
from datetime import datetime
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth.email_verification import (
    EmailMessage,
    EmailQueue,
    EmailVerification,
    EmailVerificationRepository,
)

logger = logging.getLogger(__name__)


class EmailVerificationsPg(EmailVerificationRepository):
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    def _row_to_model(self, row) -> EmailVerification:
        return EmailVerification(
            id=row["id"],
            email=row["email"],
            code_hash=row["code_hash"],
            created_at=row["created_at"],
            code_expires_at=row["code_expires_at"],
            verified_at=row["verified_at"],
            verification_expires_at=row["verification_expires_at"],
            used_at=row["used_at"],
        )

    async def create_pending(
        self,
        verification_id: UUID,
        email: str,
        code_hash: str,
        code_expires_at: datetime,
    ) -> EmailVerification:
        result = await self._conn.execute(
            text(
                """
                INSERT INTO email_verifications (
                    id,
                    email,
                    code_hash,
                    code_expires_at
                )
                VALUES (
                    :id,
                    :email,
                    :code_hash,
                    :code_expires_at
                )
                RETURNING
                    id,
                    email,
                    code_hash,
                    created_at,
                    code_expires_at,
                    verified_at,
                    verification_expires_at,
                    used_at
                """
            ),
            {
                "id": verification_id,
                "email": email,
                "code_hash": code_hash,
                "code_expires_at": code_expires_at,
            },
        )
        row = result.mappings().one()
        return self._row_to_model(row)

    async def delete_pending_for_email(self, email: str) -> None:
        await self._conn.execute(
            text(
                """
                DELETE FROM email_verifications
                WHERE email = :email
                  AND verified_at IS NULL
                """
            ),
            {"email": email},
        )

    async def get_latest_pending(self, email: str) -> EmailVerification | None:
        result = await self._conn.execute(
            text(
                """
                SELECT
                    id,
                    email,
                    code_hash,
                    created_at,
                    code_expires_at,
                    verified_at,
                    verification_expires_at,
                    used_at
                FROM email_verifications
                WHERE email = :email
                  AND verified_at IS NULL
                  AND code_expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"email": email},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return self._row_to_model(row)

    async def mark_verified(
        self,
        verification_id: UUID,
        verified_at: datetime,
        verification_expires_at: datetime,
    ) -> EmailVerification:
        result = await self._conn.execute(
            text(
                """
                UPDATE email_verifications
                SET
                    verified_at = :verified_at,
                    verification_expires_at = :verification_expires_at
                WHERE id = :id
                  AND verified_at IS NULL
                  AND used_at IS NULL
                RETURNING
                    id,
                    email,
                    code_hash,
                    created_at,
                    code_expires_at,
                    verified_at,
                    verification_expires_at,
                    used_at
                """
            ),
            {
                "id": verification_id,
                "verified_at": verified_at,
                "verification_expires_at": verification_expires_at,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise LookupError("Email verification not found or already processed")
        return self._row_to_model(row)

    async def get_active_verified(self, verification_id: UUID) -> EmailVerification:
        result = await self._conn.execute(
            text(
                """
                SELECT
                    id,
                    email,
                    code_hash,
                    created_at,
                    code_expires_at,
                    verified_at,
                    verification_expires_at,
                    used_at
                FROM email_verifications
                WHERE id = :id
                  AND verified_at IS NOT NULL
                  AND used_at IS NULL
                  AND verification_expires_at > NOW()
                """
            ),
            {"id": verification_id},
        )
        row = result.mappings().first()
        if row is None:
            raise LookupError("Active email verification not found")
        return self._row_to_model(row)

    async def mark_used(self, verification_id: UUID, used_at: datetime) -> None:
        result = await self._conn.execute(
            text(
                """
                UPDATE email_verifications
                SET used_at = :used_at
                WHERE id = :id
                  AND verified_at IS NOT NULL
                  AND used_at IS NULL
                  AND verification_expires_at > NOW()
                """
            ),
            {"id": verification_id, "used_at": used_at},
        )
        if result.rowcount == 0:
            raise LookupError("Active email verification not found")


class RedisEmailQueue(EmailQueue):
    def __init__(self, client: redis.Redis, queue_key: str) -> None:
        self._client = client
        self._queue_key = queue_key

    async def enqueue(self, message: EmailMessage) -> None:
        payload = json.dumps(
            {
                "to": message.to,
                "subject": message.subject,
                "body_text": message.body_text,
            },
            ensure_ascii=False,
        )
        await self._client.lpush(self._queue_key, payload)

    async def dequeue(self, timeout_seconds: int = 5) -> EmailMessage | None:
        """Извлекает следующее письмо из очереди (для worker)."""
        try:
            item = await self._client.brpop(
                self._queue_key,
                timeout=timeout_seconds,
            )
        except redis.TimeoutError:
            return None

        if item is None:
            return None
        _, payload = item
        data = json.loads(payload)
        return EmailMessage(
            to=data["to"],
            subject=data["subject"],
            body_text=data["body_text"],
        )


class VerificationCodeHasher:
    def __init__(self, pepper: str) -> None:
        self._pepper = pepper

    def hash_code(self, email: str, code: str) -> str:
        digest = hashlib.sha256(f"{self._pepper}:{email}:{code}".encode())
        return digest.hexdigest()

    def verify(self, email: str, code: str, code_hash: str) -> bool:
        return self.hash_code(email, code) == code_hash
