from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.exceptions import TagNotFoundError
from core.models import Tag
from core.tutors import Tags


class TagsPg(Tags):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def link_tag_to_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        if not await self.is_exists(tag_name):
            raise TagNotFoundError

        await self._connection.execute(
            text(
                """
                INSERT INTO profile_tags (tutor_id, tag_name)
                VALUES (:tutor_id, :tag_name)
                """
            ),
            dict(tutor_id=tutor_id, tag_name=tag_name),
        )

    async def unlink_tag_from_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        if not await self.is_exists(tag_name):
            raise TagNotFoundError

        await self._connection.execute(
            text(
                """
                DELETE FROM profile_tags
                WHERE tutor_id = :tutor_id AND tag_name = :tag_name
                """
            ),
            dict(tutor_id=tutor_id, tag_name=tag_name),
        )

    async def get_tags_by_tutor(self, tutor_id: UUID) -> list[Tag]:
        result = await self._connection.execute(
            text(
                """
                SELECT tag_name
                FROM profile_tags
                WHERE tutor_id = :tutor_id
                ORDER BY created_at
                """
            ),
            dict(tutor_id=tutor_id),
        )
        return [Tag(name=row["tag_name"]) for row in result.mappings()]

    async def add(self, tag_name: str) -> None:
        await self._connection.execute(
            text(
                """
                INSERT INTO tags (name)
                VALUES (:name)
                """
            ),
            dict(name=tag_name),
        )

    async def remove(self, tag_name: str) -> None:
        if not await self.is_exists(tag_name):
            raise TagNotFoundError

        await self._connection.execute(
            text(
                """
                DELETE FROM tags
                WHERE name = :name
                """
            ),
            dict(name=tag_name),
        )

    async def is_exists(self, tag_name: str) -> bool:
        result = await self._connection.execute(
            text(
                """
                SELECT 1
                FROM tags
                WHERE name = :name
                """
            ),
            dict(name=tag_name),
        )
        return result.first() is not None

    async def get(self, tag_name: str) -> Tag:
        if not await self.is_exists(tag_name):
            raise TagNotFoundError

        return Tag(name=tag_name)

    async def get_all(self) -> list[Tag]:
        result = await self._connection.execute(
            text(
                """
                SELECT name
                FROM tags
                ORDER BY created_at
                """
            ),
        )
        return [Tag(name=row["name"]) for row in result.mappings()]
