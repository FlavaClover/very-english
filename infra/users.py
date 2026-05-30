from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth.exceptions import UserNotFoundError
from auth.models import User, UserRole
from auth.users import Users


class UsersPg(Users):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    def _row_to_user(self, row) -> User:
        return User(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            role=UserRole(str(row["role"])),
            photo=row["photo"],
        )

    async def create(self, user: User, password_hash: str) -> User:
        await self._connection.execute(
            text(
                """
                INSERT INTO users (
                    id,
                    photo,
                    first_name,
                    last_name,
                    email,
                    password_hash,
                    role
                )
                VALUES (
                    :id,
                    :photo,
                    :first_name,
                    :last_name,
                    :email,
                    :password_hash,
                    CAST(:role AS user_role)
                )
                """
            ),
            dict(
                id=user.id,
                photo=user.photo,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                password_hash=password_hash,
                role=user.role.value,
            ),
        )
        return user

    async def get(self, user_id: UUID) -> User:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    photo,
                    first_name,
                    last_name,
                    email,
                    role::text AS role
                FROM users
                WHERE id = :user_id
                """
            ),
            dict(user_id=user_id),
        )
        row = result.mappings().first()
        if row is None:
            raise UserNotFoundError

        return self._row_to_user(row)

    async def get_by_email(self, email: str) -> User:
        result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    photo,
                    first_name,
                    last_name,
                    email,
                    role::text AS role
                FROM users
                WHERE email = :email
                """
            ),
            dict(email=email),
        )
        row = result.mappings().first()
        if row is None:
            raise UserNotFoundError

        return self._row_to_user(row)

    async def get_password_hash(self, user_id: UUID) -> str:
        result = await self._connection.execute(
            text(
                """
                SELECT password_hash
                FROM users
                WHERE id = :user_id
                """
            ),
            dict(user_id=user_id),
        )
        row = result.mappings().first()
        if row is None:
            raise UserNotFoundError

        return row["password_hash"]

    async def update(self, user_id: UUID, user: User) -> User:
        result = await self._connection.execute(
            text(
                """
                UPDATE users
                SET
                    first_name = :first_name,
                    last_name = :last_name,
                    email = :email,
                    role = CAST(:role AS user_role)
                WHERE id = :user_id
                """
            ),
            dict(
                user_id=user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                role=user.role.value,
            ),
        )
        if result.rowcount == 0:
            raise UserNotFoundError

        return User(
            id=user_id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role=user.role,
            photo=user.photo,
        )

    async def set_photo(self, user_id: UUID, photo: str | None) -> User:
        result = await self._connection.execute(
            text(
                """
                UPDATE users
                SET photo = :photo
                WHERE id = :user_id
                RETURNING
                    id,
                    photo,
                    first_name,
                    last_name,
                    email,
                    role::text AS role
                """
            ),
            dict(user_id=user_id, photo=photo),
        )
        row = result.mappings().first()
        if row is None:
            raise UserNotFoundError

        return self._row_to_user(row)

    async def is_email_taken(self, email: str) -> bool:
        result = await self._connection.execute(
            text(
                """
                SELECT 1
                FROM users
                WHERE email = :email
                """
            ),
            dict(email=email),
        )
        return result.first() is not None

    async def link_tutor(self, user_id: UUID, tutor_id: UUID) -> None:
        await self._connection.execute(
            text(
                """
                INSERT INTO users_tutor (user_id, tutor_id)
                VALUES (:user_id, :tutor_id)
                """
            ),
            dict(user_id=user_id, tutor_id=tutor_id),
        )

    async def get_tutor_id(self, user_id: UUID) -> UUID | None:
        result = await self._connection.execute(
            text(
                """
                SELECT tutor_id
                FROM users_tutor
                WHERE user_id = :user_id
                """
            ),
            dict(user_id=user_id),
        )
        row = result.mappings().first()
        if row is None:
            return None

        return row["tutor_id"]
