from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.views import TutorProfileView, TutorProfileViews


class TutorProfileViewsPg(TutorProfileViews):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def upsert_view(self, user_id: UUID, tutor_id: UUID) -> None:
        await self._connection.execute(
            text(
                """
                INSERT INTO tutor_profile_views (user_id, tutor_id, viewed_at)
                VALUES (:user_id, :tutor_id, :viewed_at)
                ON CONFLICT (user_id, tutor_id) DO UPDATE SET
                    viewed_at = EXCLUDED.viewed_at
                """
            ),
            dict(
                user_id=user_id,
                tutor_id=tutor_id,
                viewed_at=datetime.now(UTC),
            ),
        )

    async def list_recent(
        self,
        user_id: UUID,
        limit: int,
    ) -> list[TutorProfileView]:
        result = await self._connection.execute(
            text(
                """
                SELECT tutor_id, viewed_at
                FROM tutor_profile_views
                WHERE user_id = :user_id
                ORDER BY viewed_at DESC
                LIMIT :limit
                """
            ),
            dict(user_id=user_id, limit=limit),
        )
        return [
            TutorProfileView(
                tutor_id=row["tutor_id"],
                viewed_at=row["viewed_at"],
            )
            for row in result.mappings()
        ]
