from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.exceptions import TutorNotFoundError
from core.models import (
    Level,
    Tutor,
    TutorStatus,
    TutorStatusHistory,
    WorkFormat,
)
from core.tutors import Tutors


class TutorsPg(Tutors):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def get(self, tutor_id: UUID) -> Tutor:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    description,
                    cities,
                    levels::text[] AS levels,
                    price,
                    lesson_duration,
                    work_format::text AS work_format
                FROM tutors
                WHERE id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        row = result.mappings().first()
        if row is None:
            raise TutorNotFoundError

        return Tutor(
            id=row["id"],
            description=row["description"],
            cities=list(row["cities"]),
            levels=[Level(level) for level in row["levels"]],
            price=row["price"],
            lesson_duration=row["lesson_duration"],
            work_format=WorkFormat(row["work_format"]),
        )

    async def create(self, tutor: Tutor) -> Tutor:
        await self._connection.execute(
            text(
                """
                INSERT INTO tutors (
                    id,
                    description,
                    cities,
                    levels,
                    price,
                    lesson_duration,
                    work_format
                )
                VALUES (
                    :id,
                    :description,
                    :cities,
                    CAST(:levels AS tutor_level[]),
                    :price,
                    :lesson_duration,
                    CAST(:work_format AS tutor_work_format)
                )
                """
            ),
            dict(
                id=tutor.id,
                description=tutor.description,
                cities=tutor.cities,
                levels=[level.value for level in tutor.levels],
                price=tutor.price,
                lesson_duration=tutor.lesson_duration,
                work_format=tutor.work_format.value,
            ),
        )
        return tutor

    async def update(self, tutor_id: UUID, tutor: Tutor) -> Tutor:
        result = await self._connection.execute(
            text(
                """
                UPDATE tutors
                SET
                    description = :description,
                    cities = :cities,
                    levels = CAST(:levels AS tutor_level[]),
                    price = :price,
                    lesson_duration = :lesson_duration,
                    work_format = CAST(:work_format AS tutor_work_format)
                WHERE id = :tutor_id
                """
            ),
            dict(
                tutor_id=tutor_id,
                description=tutor.description,
                cities=tutor.cities,
                levels=[level.value for level in tutor.levels],
                price=tutor.price,
                lesson_duration=tutor.lesson_duration,
                work_format=tutor.work_format.value,
            ),
        )
        if result.rowcount == 0:
            raise TutorNotFoundError

        return Tutor(
            id=tutor_id,
            description=tutor.description,
            cities=tutor.cities,
            levels=tutor.levels,
            price=tutor.price,
            lesson_duration=tutor.lesson_duration,
            work_format=tutor.work_format,
        )

    async def set_status(self, tutor_id: UUID, status: TutorStatus) -> Tutor:
        tutor = await self.get(tutor_id)
        await self._connection.execute(
            text(
                """
                INSERT INTO status_history (id, tutor_id, status)
                VALUES (:id, :tutor_id, CAST(:status AS tutor_status))
                """
            ),
            dict(
                id=uuid4(),
                tutor_id=tutor_id,
                status=status.value,
            ),
        )
        return tutor

    async def statuses(self, tutor_id: UUID) -> list[TutorStatusHistory]:
        result = await self._connection.execute(
            text(
                """
                SELECT id, status, created_at
                FROM status_history
                WHERE tutor_id = :tutor_id
                ORDER BY seq
                """
            ),
            dict(tutor_id=tutor_id),
        )
        return [
            TutorStatusHistory(
                id=row["id"],
                status=TutorStatus(str(row["status"])),
                created_at=row["created_at"],
            )
            for row in result.mappings()
        ]
