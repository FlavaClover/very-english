from abc import ABC, abstractmethod

import bcrypt


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str:
        """Возвращает хеш пароля."""

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        """Проверяет соответствие пароля хешу."""


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        """Хеширует пароль через bcrypt.

        :param password: Пароль в открытом виде.
        :return: Строка с bcrypt-хешем.
        """
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify(self, password: str, password_hash: str) -> bool:
        """Сверяет пароль с bcrypt-хешем.

        :param password: Пароль в открытом виде.
        :param password_hash: Сохранённый bcrypt-хеш.
        :return: True, если пароль совпадает.
        """
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
