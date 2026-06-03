from uuid import UUID, uuid4
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
    Point,
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
        page: int = 1,
        page_size: int = 10,
    ) -> list[TutorProfile]:
        """
        Filter tutors by price, levels, work formats, cities, tags.
        Getting tutors with status APPROVED.

        By raw SQL query.
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


class AbstractTutorManager(ABC):
    @abstractmethod
    async def create(
        self,
        description: str,
        cities: list[str],
        levels: list[Level],
        price: int,
        lesson_duration: int,
        work_format: WorkFormat,
        contacts: list[Contact],
        tags: list[Tag],
    ) -> Tutor:
        pass

    @abstractmethod
    async def update(self, tutor_id: UUID, tutor: Tutor) -> Tutor:
        pass

    @abstractmethod
    async def set_status(self, tutor_id: UUID, status: TutorStatus) -> Tutor:
        pass

    @abstractmethod
    async def get_contacts(self, tutor_id: UUID) -> list[Contact]:
        pass

    @abstractmethod
    async def add_contact(self, tutor_id: UUID, name: str, value: str) -> Tutor:
        pass

    @abstractmethod
    async def remove_contact(self, tutor_id: UUID, name: str) -> Tutor:
        pass

    @abstractmethod
    async def add_achievement(
        self, tutor_id: UUID, path: Path | PathLike | str, name: str
    ) -> Achievement:
        pass

    @abstractmethod
    async def get_achievements(self, tutor_id: UUID) -> list[Achievement]:
        pass

    @abstractmethod
    async def remove_achievement(self, tutor_id: UUID, name: str) -> None:
        pass

    @abstractmethod
    async def link_tag_to_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        pass

    @abstractmethod
    async def unlink_tag_from_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        pass

    @abstractmethod
    async def add_advantage(
        self,
        tutor_id: UUID,
        points: list[Point],
        video: Path | PathLike | str,
        name: str,
    ) -> Advantage:
        pass

    @abstractmethod
    async def set_advantage(
        self,
        tutor_id: UUID,
        points: list[Point],
        video: Path | PathLike | str,
        name: str,
    ) -> Advantage:
        pass

    @abstractmethod
    async def upload_visit_video(
        self,
        tutor_id: UUID,
        video: Path | PathLike | str,
        name: str,
    ) -> Advantage:
        pass

    @abstractmethod
    async def get_advantage(self, tutor_id: UUID) -> Advantage:
        pass

    @abstractmethod
    async def remove_advantage(self, tutor_id: UUID) -> None:
        pass


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


class TutorManager(AbstractTutorManager):
    def __init__(
        self,
        tutors: Tutors,
        tags: Tags,
        contacts: Contacts,
        achievements: Achievements,
        advantages: Advantages,
        media: Media,
    ) -> None:
        self.tutors = tutors
        self.contacts = contacts
        self.achievements = achievements
        self.tags = tags
        self.media = media
        self.advantages = advantages

    async def create(
        self,
        description: str,
        cities: list[str],
        levels: list[Level],
        price: int,
        lesson_duration: int,
        work_format: WorkFormat,
        contacts: list[Contact],
        tags: list[Tag],
    ) -> Tutor:
        tutor = Tutor(
            id=uuid4(),
            description=description,
            cities=cities,
            levels=levels,
            price=price,
            lesson_duration=lesson_duration,
            work_format=work_format,
        )

        if len(cities) == 0:
            raise ValueError("Cities cannot be empty")

        if len(levels) == 0:
            raise ValueError("Levels cannot be empty")

        if price <= 0:
            raise ValueError("Price must be greater than 0")

        if lesson_duration <= 0:
            raise ValueError("Lesson duration must be greater than 0")

        if len(contacts) == 0:
            raise ValueError("Contacts cannot be empty")

        if len(tags) == 0:
            raise ValueError("Tags cannot be empty")

        contact_names = [contact.name for contact in contacts]
        if len(contact_names) != len(set(contact_names)):
            raise ValueError("Contacts must be unique")

        tutor = await self.tutors.create(tutor)
        await self.set_status(tutor.id, TutorStatus.DRAFT)

        for contact in contacts:
            await self.add_contact(tutor.id, contact.name, contact.value)

        for tag in tags:
            await self.link_tag_to_tutor(tutor.id, tag.name)

        return tutor

    async def update(self, tutor_id: UUID, tutor: Tutor) -> Tutor:
        return await self.tutors.update(tutor_id, tutor)

    async def set_status(self, tutor_id: UUID, status: TutorStatus) -> Tutor:
        return await self.tutors.set_status(tutor_id, status)

    async def get_contacts(self, tutor_id: UUID) -> list[Contact]:
        return await self.contacts.get(tutor_id)

    async def add_contact(self, tutor_id: UUID, name: str, value: str) -> Tutor:
        contacts = await self.get_contacts(tutor_id)
        if name in [contact.name for contact in contacts]:
            raise ValueError(f"Contact {name} already exists")

        return await self.contacts.add(tutor_id, Contact(name=name, value=value))

    async def remove_contact(self, tutor_id: UUID, name: str) -> Tutor:
        contacts = await self.get_contacts(tutor_id)
        if name not in [contact.name for contact in contacts]:
            raise ValueError(f"Contact {name} does not exist")

        return await self.contacts.remove(tutor_id, name)

    async def add_achievement(
        self, tutor_id: UUID, path: Path | PathLike | str, name: str
    ) -> Achievement:
        await self.media.add(path, name)
        return await self.achievements.add(tutor_id, Achievement(image=name))

    async def get_achievements(self, tutor_id: UUID) -> list[Achievement]:
        return await self.achievements.get(tutor_id)

    async def remove_achievement(self, tutor_id: UUID, name: str) -> None:
        achievements = await self.get_achievements(tutor_id)
        if name not in [achievement.image for achievement in achievements]:
            raise ValueError(f"Achievement {name} does not exist")

        await self.media.remove(name)
        await self.achievements.remove(tutor_id, name)

    async def link_tag_to_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        if not await self.tags.is_exists(tag_name):
            raise ValueError(f"Tag {tag_name} does not exist")

        tags = await self.tags.get_tags_by_tutor(tutor_id)
        if tag_name in [tag.name for tag in tags]:
            raise ValueError(f"Tag {tag_name} is already linked to tutor {tutor_id}")

        await self.tags.link_tag_to_tutor(tutor_id, tag_name)

    async def unlink_tag_from_tutor(self, tutor_id: UUID, tag_name: str) -> None:
        if not await self.tags.is_exists(tag_name):
            raise ValueError(f"Tag {tag_name} does not exist")

        tags = await self.tags.get_tags_by_tutor(tutor_id)
        if tag_name not in [tag.name for tag in tags]:
            raise ValueError(f"Tag {tag_name} is not linked to tutor {tutor_id}")

        await self.tags.unlink_tag_from_tutor(tutor_id, tag_name)

    async def add_advantage(
        self,
        tutor_id: UUID,
        points: list[Point],
        video: Path | PathLike | str,
        name: str,
    ) -> Advantage:
        await self.media.add(video, name)
        return await self.advantages.add(tutor_id, Advantage(points=points, video=name))

    async def get_advantage(self, tutor_id: UUID) -> Advantage:
        if not await self.advantages.is_exists(tutor_id):
            raise ValueError("Advantage does not exist")

        advantage = await self.advantages.get(tutor_id)
        if advantage is None:
            raise ValueError("Advantage does not exist")

        return advantage

    async def set_advantage(
        self,
        tutor_id: UUID,
        points: list[Point],
        video: Path | PathLike | str,
        name: str,
    ) -> Advantage:
        if await self.advantages.is_exists(tutor_id):
            existing = await self.get_advantage(tutor_id)
            await self.media.remove(existing.video)
            await self.media.add(video, name)
            return await self.advantages.update(
                tutor_id,
                Advantage(points=points, video=name),
            )

        return await self.add_advantage(tutor_id, points, video, name)

    async def upload_visit_video(
        self,
        tutor_id: UUID,
        video: Path | PathLike | str,
        name: str,
    ) -> Advantage:
        if await self.advantages.is_exists(tutor_id):
            existing = await self.get_advantage(tutor_id)
            await self.media.remove(existing.video)
            await self.media.add(video, name)
            return await self.advantages.update(
                tutor_id,
                Advantage(points=existing.points, video=name),
            )

        return await self.add_advantage(tutor_id, [], video, name)

    async def remove_advantage(self, tutor_id: UUID) -> None:
        if not await self.advantages.is_exists(tutor_id):
            raise ValueError("Advantage does not exist")

        advantage = await self.get_advantage(tutor_id)
        await self.media.remove(advantage.video)
        await self.advantages.remove(tutor_id)


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
