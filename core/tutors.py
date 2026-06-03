from uuid import UUID
from os import PathLike
from pathlib import Path
from abc import ABC, abstractmethod
from core.models import (
    Tutor,
    TutorStatus,
    Contact,
    Level,
    WorkFormat,
    Tag,
    Achievement,
    TutorProfile,
    Advantage,
    TutorStatusHistory,
)


class Media(ABC):
    @abstractmethod
    async def add(self, value: Path | PathLike | str, name: str):
        pass

    @abstractmethod
    async def remove(self, name: str):
        pass

    @abstractmethod
    async def url(self, name: str) -> str:
        """Возвращает URL для доступа к объекту по ключу в хранилище.

        :param name: Ключ объекта.
        :return: Временная ссылка на файл.
        """
        pass


class Contacts(ABC):
    @abstractmethod
    async def add(self, tutor_id: UUID, contact: Contact) -> Tutor:
        pass

    @abstractmethod
    async def remove(self, tutor_id: UUID, name: str) -> Tutor:
        pass

    @abstractmethod
    async def get(self, tutor_id: UUID) -> list[Contact]:
        pass


class Tags(ABC):
    @abstractmethod
    async def link_tag_to_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        """
        Link tag to tutor.
        By raw SQL query.

        raises:
            - TagNotFoundError: if tag not found
        """
        pass

    @abstractmethod
    async def unlink_tag_from_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        """
        Unlink tag from tutor.
        By raw SQL query.

        raises:
            - TagNotFoundError: if tag not found
        """
        pass

    @abstractmethod
    async def get_tags_by_tutor(self, tutor_id: UUID) -> list[Tag]:
        """
        Get tags by tutor.
        By raw SQL query.
        """
        pass

    @abstractmethod
    async def add(self, tag_name: str) -> None:
        pass

    @abstractmethod
    async def remove(self, tag_name: str) -> None:
        pass

    @abstractmethod
    async def is_exists(self, tag_name: str) -> bool:
        """
        Check if tag exists.
        By raw SQL query.
        """
        pass

    @abstractmethod
    async def get(self, tag_name: str) -> Tag:
        """
        Get tag by name.
        By raw SQL query.

        raises:
            - TagNotFoundError: if tag not found
        """
        pass

    @abstractmethod
    async def get_all(self) -> list[Tag]:
        """
        Get all tags.
        By raw SQL query.
        """
        pass


class Achievements(ABC):
    @abstractmethod
    async def add(self, tutor_id: UUID, achievement: Achievement) -> Achievement:
        pass

    @abstractmethod
    async def remove(self, tutor_id: UUID, image: str) -> None:
        pass

    @abstractmethod
    async def get(self, tutor_id: UUID) -> list[Achievement]:
        """
        Get achievements by tutor.
        By raw SQL query.
        """
        pass


class Advantages(ABC):
    @abstractmethod
    async def add(self, tutor_id: UUID, advantage: Advantage) -> Advantage:
        pass

    @abstractmethod
    async def remove(self, tutor_id: UUID) -> None:
        pass

    @abstractmethod
    async def get(self, tutor_id: UUID) -> Advantage | None:
        """
        Get advantage by tutor.
        By raw SQL query.
        """
        pass

    @abstractmethod
    async def update(self, tutor_id: UUID, advantage: Advantage) -> Advantage:
        """
        Rewrite advantage.
        By raw SQL query.
        """
        pass

    @abstractmethod
    async def is_exists(self, tutor_id: UUID) -> bool:
        """
        Check if advantage exists.
        By raw SQL query.
        """
        pass


class Tutors(ABC):
    @abstractmethod
    async def get(self, tutor_id: UUID) -> Tutor:
        """
        Get tutor by id.
        By raw SQL query.

        raises:
            - TutorNotFoundError: if tutor not found
        """
        pass

    @abstractmethod
    async def create(self, tutor: Tutor) -> Tutor:
        """
        Create tutor.
        By raw SQL query.
        """
        pass

    @abstractmethod
    async def update(self, tutor_id: UUID, tutor: Tutor) -> Tutor:
        pass

    @abstractmethod
    async def set_status(self, tutor_id: UUID, status: TutorStatus) -> Tutor:
        pass

    @abstractmethod
    async def statuses(self, tutor_id: UUID) -> list[TutorStatusHistory]:
        """
        Get statuses by tutor.
        By raw SQL query.
        """
        pass


class TutorFilter(ABC):
    @abstractmethod
    async def filter(
        self,
        price_from: int | None = None,
        price_to: int | None = None,
        levels: list[Level] | None = None,
        work_formats: list[WorkFormat] | None = None,
        cities: list[str] | None = None,
        tags: list[Tag] | None = None,
        pro_only: bool = False,
        page: int = 1,
        page_size: int = 10,
    ) -> list[TutorProfile]:
        """
        Filter tutors by price, levels, work formats, cities, tags.
        Getting tutors with status APPROVED and active subscription.

        :param pro_only: Если True, только туторы с активной подпиской PRO;
            иначе любой активный план (BASE или PRO).
        """
        pass

    @abstractmethod
    async def for_moderation(self) -> list[TutorProfile]:
        """
        Get tutors with status MODERATION

        By raw SQL query.
        """
        pass

    @abstractmethod
    async def get(self, tutor_id: UUID) -> TutorProfile:
        """
        Get tutor profile by id.
        By raw SQL query.

        raises:
            - TutorNotFoundError: if tutor not found
        """
        pass
