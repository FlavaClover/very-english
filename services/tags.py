from abc import ABC, abstractmethod

from core.models import Tag
from core.tutors import Tags


class AbstractTagsManager(ABC):
    @abstractmethod
    async def add(self, tag_name: str) -> None:
        pass

    @abstractmethod
    async def remove(self, tag_name: str) -> None:
        pass

    @abstractmethod
    async def get(self, tag_name: str) -> Tag:
        pass

    @abstractmethod
    async def get_all(self) -> list[Tag]:
        pass


class TagsManager(AbstractTagsManager):
    def __init__(self, tags: Tags):
        self.tags = tags

    async def add(self, tag_name: str) -> None:
        if await self.tags.is_exists(tag_name):
            raise ValueError(f"Tag {tag_name} already exists")

        await self.tags.add(tag_name)

    async def remove(self, tag_name: str) -> None:
        if not await self.tags.is_exists(tag_name):
            raise ValueError(f"Tag {tag_name} does not exist")

        await self.tags.remove(tag_name)

    async def get(self, tag_name: str) -> Tag:
        if not await self.tags.is_exists(tag_name):
            raise ValueError(f"Tag {tag_name} does not exist")

        return await self.tags.get(tag_name)

    async def get_all(self) -> list[Tag]:
        return await self.tags.get_all()
