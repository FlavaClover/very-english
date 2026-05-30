from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.models import Achievement
from core.tutors import Achievements


class AchievementsPg(Achievements):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def add(self, tutor_id: UUID, achievement: Achievement) -> Achievement:
        await self._connection.execute(
            text(
                """
                INSERT INTO achievements (tutor_id, image)
                VALUES (:tutor_id, :image)
                """
            ),
            dict(tutor_id=tutor_id, image=achievement.image),
        )
        return achievement

    async def remove(self, tutor_id: UUID, image: str) -> None:
        await self._connection.execute(
            text(
                """
                DELETE FROM achievements
                WHERE tutor_id = :tutor_id AND image = :image
                """
            ),
            dict(tutor_id=tutor_id, image=image),
        )

    async def get(self, tutor_id: UUID) -> list[Achievement]:
        result = await self._connection.execute(
            text(
                """
                SELECT image
                FROM achievements
                WHERE tutor_id = :tutor_id
                ORDER BY created_at
                """
            ),
            dict(tutor_id=tutor_id),
        )
        return [Achievement(image=row["image"]) for row in result.mappings()]
