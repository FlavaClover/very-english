from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.exceptions import TutorNotFoundError
from core.models import (
    Achievement,
    Advantage,
    Contact,
    Level,
    Point,
    Tag,
    TutorProfile,
    TutorStatus,
    WorkFormat,
)
from billing.subscriptions import SubscriptionPlanId, SubscriptionStatus
from core.tutors import TutorFilter


class TutorFilterPg(TutorFilter):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

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
        conditions = ["current_status.status = CAST(:status AS tutor_status)"]
        params: dict = dict(
            status=TutorStatus.APPROVED.value,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        if price_from is not None:
            conditions.append("t.price >= :price_from")
            params["price_from"] = price_from

        if price_to is not None:
            conditions.append("t.price <= :price_to")
            params["price_to"] = price_to

        if levels is not None and len(levels) > 0:
            conditions.append("t.levels && CAST(:levels AS tutor_level[])")
            params["levels"] = [level.value for level in levels]

        if work_formats is not None and len(work_formats) > 0:
            conditions.append(
                "t.work_format = ANY(CAST(:work_formats AS tutor_work_format[]))"
            )
            params["work_formats"] = [work_format.value for work_format in work_formats]

        if cities is not None and len(cities) > 0:
            conditions.append("t.cities && CAST(:cities AS TEXT[])")
            params["cities"] = cities

        if tags is not None and len(tags) > 0:
            conditions.append(
                """
                t.id IN (
                    SELECT tutor_id
                    FROM profile_tags
                    WHERE tag_name = ANY(CAST(:tag_names AS TEXT[]))
                    GROUP BY tutor_id
                    HAVING COUNT(DISTINCT tag_name) = :tags_count
                )
                """
            )
            params["tag_names"] = [tag.name for tag in tags]
            params["tags_count"] = len(tags)

        if pro_only:
            conditions.append(
                """
                EXISTS (
                    SELECT 1
                    FROM users_tutor ut
                    INNER JOIN tutor_subscriptions ts ON ts.user_id = ut.user_id
                    WHERE ut.tutor_id = t.id
                      AND ts.plan_id = CAST(:pro_plan AS subscription_plan)
                      AND ts.status = CAST(:active_status AS subscription_status)
                )
                """
            )
            params["pro_plan"] = SubscriptionPlanId.PRO.value
            params["active_status"] = SubscriptionStatus.ACTIVE.value
        else:
            conditions.append(
                """
                EXISTS (
                    SELECT 1
                    FROM users_tutor ut
                    INNER JOIN tutor_subscriptions ts ON ts.user_id = ut.user_id
                    WHERE ut.tutor_id = t.id
                      AND ts.status = CAST(:active_status AS subscription_status)
                )
                """
            )
            params["active_status"] = SubscriptionStatus.ACTIVE.value

        where_clause = " AND ".join(conditions)
        result = await self._connection.execute(
            text(
                f"""
                SELECT t.id
                FROM tutors t
                INNER JOIN (
                    SELECT sh.tutor_id, sh.status
                    FROM status_history sh
                    INNER JOIN (
                        SELECT tutor_id, MAX(seq) AS max_seq
                        FROM status_history
                        GROUP BY tutor_id
                    ) latest ON latest.tutor_id = sh.tutor_id
                        AND latest.max_seq = sh.seq
                ) current_status ON current_status.tutor_id = t.id
                WHERE {where_clause}
                ORDER BY t.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        tutor_ids = [row["id"] for row in result.mappings()]
        profiles: list[TutorProfile] = []
        for tutor_id in tutor_ids:
            profiles.append(await self._load_profile(tutor_id))
        return profiles

    async def for_moderation(self) -> list[TutorProfile]:
        result = await self._connection.execute(
            text(
                """
                SELECT t.id
                FROM tutors t
                INNER JOIN (
                    SELECT sh.tutor_id, sh.status
                    FROM status_history sh
                    INNER JOIN (
                        SELECT tutor_id, MAX(seq) AS max_seq
                        FROM status_history
                        GROUP BY tutor_id
                    ) latest ON latest.tutor_id = sh.tutor_id
                        AND latest.max_seq = sh.seq
                ) current_status ON current_status.tutor_id = t.id
                WHERE current_status.status = CAST(:status AS tutor_status)
                ORDER BY t.created_at DESC
                """
            ),
            dict(status=TutorStatus.MODERATION.value),
        )
        tutor_ids = [row["id"] for row in result.mappings()]
        profiles: list[TutorProfile] = []
        for tutor_id in tutor_ids:
            profiles.append(await self._load_profile(tutor_id))
        return profiles

    async def get(self, tutor_id: UUID) -> TutorProfile:
        result = await self._connection.execute(
            text(
                """
                SELECT 1
                FROM tutors
                WHERE id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        if result.first() is None:
            raise TutorNotFoundError

        return await self._load_profile(tutor_id)

    async def _load_profile(self, tutor_id: UUID) -> TutorProfile:
        tutor_result = await self._connection.execute(
            text(
                """
                SELECT
                    id,
                    description,
                    cities,
                    levels::text[] AS levels,
                    price,
                    lesson_duration,
                    work_format::text AS work_format
                FROM tutors
                WHERE id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        tutor_row = tutor_result.mappings().first()
        if tutor_row is None:
            raise TutorNotFoundError

        status_result = await self._connection.execute(
            text(
                """
                SELECT status
                FROM status_history
                WHERE tutor_id = :tutor_id
                ORDER BY seq DESC
                LIMIT 1
                """
            ),
            dict(tutor_id=tutor_id),
        )
        status_row = status_result.mappings().first()
        if status_row is None:
            raise TutorNotFoundError

        contacts_result = await self._connection.execute(
            text(
                """
                SELECT name, value
                FROM contacts
                WHERE tutor_id = :tutor_id
                ORDER BY created_at
                """
            ),
            dict(tutor_id=tutor_id),
        )
        contacts = [
            Contact(name=row["name"], value=row["value"])
            for row in contacts_result.mappings()
        ]

        tags_result = await self._connection.execute(
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
        tags = [Tag(name=row["tag_name"]) for row in tags_result.mappings()]

        achievements_result = await self._connection.execute(
            text(
                """
                SELECT image
                FROM achievements
                WHERE tutor_id = :tutor_id
                ORDER BY created_at
                """
            ),
            dict(tutor_id=tutor_id),
        )
        achievements = [
            Achievement(image=row["image"]) for row in achievements_result.mappings()
        ]

        video_result = await self._connection.execute(
            text(
                """
                SELECT video
                FROM videos
                WHERE tutor_id = :tutor_id
                """
            ),
            dict(tutor_id=tutor_id),
        )
        video_row = video_result.mappings().first()
        if video_row is None:
            advantage = Advantage(video="", points=[])
        else:
            points_result = await self._connection.execute(
                text(
                    """
                    SELECT text
                    FROM points
                    WHERE tutor_id = :tutor_id
                    ORDER BY seq
                    """
                ),
                dict(tutor_id=tutor_id),
            )
            advantage = Advantage(
                video=video_row["video"],
                points=[Point(text=row["text"]) for row in points_result.mappings()],
            )

        return TutorProfile(
            id=tutor_row["id"],
            description=tutor_row["description"],
            cities=list(tutor_row["cities"]),
            levels=[Level(level) for level in tutor_row["levels"]],
            price=tutor_row["price"],
            lesson_duration=tutor_row["lesson_duration"],
            work_format=WorkFormat(tutor_row["work_format"]),
            status=TutorStatus(str(status_row["status"])),
            achievements=achievements,
            advantage=advantage,
            contacts=contacts,
            tags=tags,
        )
