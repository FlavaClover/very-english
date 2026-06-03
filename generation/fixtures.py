import random
import secrets
import string
from uuid import uuid4

from mimesis import Address, Person, Text
from mimesis.locales import Locale

from auth.models import User, UserRole
from core.models import Contact, Level, Tutor, TutorStatus, WorkFormat


class ProfileFixtures:
    """Случайные текстовые данные для анкет через mimesis."""

    def __init__(self) -> None:
        self._person = Person(Locale.RU)
        self._address = Address(Locale.RU)
        self._text = Text(Locale.RU)

    def tag_name(self) -> str:
        word = self._text.word().lower().replace(" ", "-")
        suffix = secrets.token_hex(2)
        return f"{word}-{suffix}"

    def first_name(self) -> str:
        return self._person.first_name()

    def last_name(self) -> str:
        return self._person.last_name()

    def description(self) -> str:
        return self._text.text(quantity=2).strip()

    def city(self) -> str:
        return self._address.city()

    def cities(self, count: int = 2) -> list[str]:
        return [self.city() for _ in range(count)]

    def advantage_point(self) -> str:
        return self._text.sentence().strip()

    def contact_value(self, name: str) -> str:
        if name == "telegram":
            return f"@{self._person.username()}"
        if name == "whatsapp":
            return self._person.telephone()
        if name == "email":
            return self._person.email()
        return self._person.telephone()

    def password(self) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(12))

    def email(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:10]}@generated.local"

    def levels(self) -> list[Level]:
        all_levels = list(Level)
        count = random.randint(1, min(4, len(all_levels)))
        return random.sample(all_levels, k=count)

    def work_format(self) -> WorkFormat:
        return random.choice(list(WorkFormat))

    def price(self) -> int:
        return random.randint(800, 4500) // 50 * 50

    def lesson_duration(self) -> int:
        return random.choice([45, 60, 90])

    def tutor_status(self, index: int) -> TutorStatus:
        statuses = list(TutorStatus)
        return statuses[index % len(statuses)]

    def contact_names(self) -> list[str]:
        pool = ["telegram", "whatsapp", "email", "phone"]
        count = random.randint(1, 3)
        return random.sample(pool, k=count)

    def pick_tags(self, pool: list[str], count: int | None = None) -> list[str]:
        if not pool:
            return []
        upper = min(len(pool), count or random.randint(2, 5))
        lower = min(upper, 2)
        pick_count = random.randint(lower, upper)
        return random.sample(pool, k=pick_count)

    def build_user(
        self,
        role: UserRole,
        email_prefix: str,
        photo_key: str | None = None,
    ) -> tuple[User, str]:
        """Собирает пользователя и открытый пароль.

        :param role: Роль аккаунта.
        :param email_prefix: Префикс для уникального email.
        :param photo_key: Ключ фото в S3.
        :return: Пара (пользователь, пароль в открытом виде).
        """
        password = self.password()
        user = User(
            id=uuid4(),
            first_name=self.first_name(),
            last_name=self.last_name(),
            email=self.email(email_prefix),
            role=role,
            photo=photo_key,
        )
        return user, password

    def build_tutor(self) -> Tutor:
        return Tutor(
            id=uuid4(),
            description=self.description(),
            cities=self.cities(random.randint(1, 3)),
            levels=self.levels(),
            price=self.price(),
            lesson_duration=self.lesson_duration(),
            work_format=self.work_format(),
        )

    def build_contacts(self) -> list[Contact]:
        return [
            Contact(name=name, value=self.contact_value(name))
            for name in self.contact_names()
        ]
