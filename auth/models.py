from uuid import UUID
from dataclasses import dataclass
from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    TUTOR = "tutor"
    USER = "user"


@dataclass
class User:
    id: UUID
    first_name: str
    last_name: str
    email: str
    role: UserRole
    photo: str | None = None
