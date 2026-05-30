from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.exceptions import TutorNotFoundError
from core.models import Contact, Level, Tutor, WorkFormat
from core.tutors import Contacts


class ContactsPg(Contacts):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def add(self, tutor_id: UUID, contact: Contact) -> Tutor:
        await self._connection.execute(
            text(
                """
                INSERT INTO contacts (tutor_id, name, value)
                VALUES (:tutor_id, :name, :value)
                """
            ),
            dict(tutor_id=tutor_id, name=contact.name, value=contact.value),
        )
        return await self._get_tutor(tutor_id)

    async def remove(self, tutor_id: UUID, name: str) -> Tutor:
        result = await self._connection.execute(
            text(
                """
                DELETE FROM contacts
                WHERE tutor_id = :tutor_id AND name = :name
                """
            ),
            dict(tutor_id=tutor_id, name=name),
        )
        if result.rowcount == 0:
            raise TutorNotFoundError

        return await self._get_tutor(tutor_id)

    async def get(self, tutor_id: UUID) -> list[Contact]:
        result = await self._connection.execute(
            text(
                """
                SELECT name, value
                FROM contacts
                WHERE tutor_id = :tutor_id
                ORDER BY created_at
                """
            ),
            dict(tutor_id=tutor_id),
        )
        return [
            Contact(name=row["name"], value=row["value"]) for row in result.mappings()
        ]

    async def _get_tutor(self, tutor_id: UUID) -> Tutor:
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
