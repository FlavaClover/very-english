from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.models import Advantage, Point
from core.tutors import Advantages


class AdvantagesPg(Advantages):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def add(self, tutor_id: UUID, advantage: Advantage) -> Advantage:
        await self._connection.execute(
            text(
                """
                INSERT INTO videos (tutor_id, video)
                VALUES (:tutor_id, :video)
                """
            ),
            dict(tutor_id=tutor_id, video=advantage.video),
        )
        for point in advantage.points:
            await self._connection.execute(
                text(
                    """
                    INSERT INTO points (id, tutor_id, text)
                    VALUES (:id, :tutor_id, :text)
                    """
                ),
                dict(id=uuid4(), tutor_id=tutor_id, text=point.text),
            )
        return advantage

    async def remove(self, tutor_id: UUID) -> None:
        await self._connection.execute(
            text(
                """
                DELETE FROM points
                WHERE tutor_id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        await self._connection.execute(
            text(
                """
                DELETE FROM videos
                WHERE tutor_id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )

    async def get(self, tutor_id: UUID) -> Advantage | None:
        video_result = await self._connection.execute(
            text(
                """
                SELECT video
                FROM videos
                WHERE tutor_id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        video_row = video_result.mappings().first()
        if video_row is None:
            return None

        points_result = await self._connection.execute(
            text(
                """
                SELECT text
                FROM points
                WHERE tutor_id = :tutor_id
                ORDER BY seq
                """
            ),
            dict(tutor_id=tutor_id),
        )
        return Advantage(
            video=video_row["video"],
            points=[Point(text=row["text"]) for row in points_result.mappings()],
        )

    async def update(self, tutor_id: UUID, advantage: Advantage) -> Advantage:
        await self._connection.execute(
            text(
                """
                UPDATE videos
                SET video = :video
                WHERE tutor_id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id, video=advantage.video),
        )
        await self._connection.execute(
            text(
                """
                DELETE FROM points
                WHERE tutor_id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        for point in advantage.points:
            await self._connection.execute(
                text(
                    """
                    INSERT INTO points (id, tutor_id, text)
                    VALUES (:id, :tutor_id, :text)
                    """
                ),
                dict(id=uuid4(), tutor_id=tutor_id, text=point.text),
            )
        return advantage

    async def is_exists(self, tutor_id: UUID) -> bool:
        result = await self._connection.execute(
            text(
                """
                SELECT 1
                FROM videos
                WHERE tutor_id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        return result.first() is not None
