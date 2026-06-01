from dataclasses import dataclass
from uuid import UUID

from auth.models import UserRole


@dataclass(slots=True)
class AuthContext:
    """Контекст аутентифицированного пользователя после проверки access JWT."""

    user_id: UUID
    role: UserRole
