from uuid import UUID
from enum import Enum
from datetime import datetime
from dataclasses import dataclass


class WorkFormat(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class Level(Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class TutorStatus(Enum):
    DRAFT = "draft"
    UNVISIBLE = "unvisible"
    MODERATION = "moderation"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Contact:
    name: str
    value: str


@dataclass
class Tag:
    name: str


@dataclass
class TutorStatusHistory:
    id: UUID
    status: TutorStatus
    created_at: datetime


@dataclass
class Achievement:
    image: str


@dataclass
class Tutor:
    id: UUID

    description: str
    cities: list[str]
    levels: list[Level]
    price: int
    lesson_duration: int
    work_format: WorkFormat


@dataclass
class Point:
    text: str


@dataclass
class Advantage:
    video: str
    points: list[Point]


@dataclass
class TutorProfile(Tutor):
    status: TutorStatus
    achievements: list[Achievement]
    advantage: Advantage
    contacts: list[Contact]
    tags: list[Tag]
