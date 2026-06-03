from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from api.schema import ErrorResponse
from api.tutors.schema import (
    AchievementResponse,
    AdvantageResponse,
    ContactResponse,
    PointResponse,
    TagResponse,
    TutorProfileResponse,
)
from auth.users import Users
from core.exceptions import TutorNotFoundError
from core.models import Level, Tag, WorkFormat
from services.subscription import AbstractSubscriptionService
from services.views import AbstractTutorProfileViewService
from core.tutors import Media, TutorFilter

router = APIRouter(prefix="/tutors", tags=["Catalog"])


@router.get(
    "",
    response_model=list[TutorProfileResponse],
    summary="Список туторов (каталог)",
)
async def list_tutors(
    tutor_filter: Annotated[TutorFilter, Depends()],
    users: Annotated[Users, Depends()],
    media: Annotated[Media, Depends()],
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
    price_from: int | None = Query(default=None, ge=0),
    price_to: int | None = Query(default=None, ge=0),
    levels: list[str] | None = Query(default=None),
    work_formats: list[str] | None = Query(default=None),
    cities: list[str] | None = Query(default=None),
    tags: list[str] | None = Query(default=None),
    pro_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> list[TutorProfileResponse]:
    parsed_levels = [Level(level) for level in levels] if levels else None
    parsed_formats = (
        [WorkFormat(value) for value in work_formats] if work_formats else None
    )
    parsed_tags = [Tag(name=name) for name in tags] if tags else None
    profiles = await tutor_filter.filter(
        price_from=price_from,
        price_to=price_to,
        levels=parsed_levels,
        work_formats=parsed_formats,
        cities=cities,
        tags=parsed_tags,
        pro_only=pro_only,
        page=page,
        page_size=page_size,
    )
    result: list[TutorProfileResponse] = []
    for profile in profiles:
        user = await users.get_by_tutor_id(profile.id)
        photo_key = user.photo if user is not None else None
        subscription_plan = None
        if user is not None:
            subscription_plan = await subscription_service.resolve_subscription_plan(
                user.id,
            )
        achievements: list[AchievementResponse] = []
        for achievement in profile.achievements:
            achievement_url = None
            if achievement.image:
                achievement_url = await media.url(achievement.image)
            achievements.append(
                AchievementResponse(
                    image=achievement.image,
                    url=achievement_url,
                )
            )
        video_url = None
        if profile.advantage.video:
            video_url = await media.url(profile.advantage.video)
        photo_url = None
        if photo_key:
            photo_url = await media.url(photo_key)
        result.append(
            TutorProfileResponse(
                id=profile.id,
                description=profile.description,
                cities=profile.cities,
                levels=[level.value for level in profile.levels],
                price=profile.price,
                lesson_duration=profile.lesson_duration,
                work_format=profile.work_format.value,
                status=profile.status.value,
                photo_url=photo_url,
                subscription_plan=subscription_plan,
                achievements=achievements,
                advantage=AdvantageResponse(
                    video=profile.advantage.video,
                    video_url=video_url,
                    points=[
                        PointResponse(text=point.text)
                        for point in profile.advantage.points
                    ],
                ),
                contacts=[
                    ContactResponse(name=contact.name, value=contact.value)
                    for contact in profile.contacts
                ],
                tags=[TagResponse(name=tag.name) for tag in profile.tags],
            )
        )
    return result


@router.get(
    "/{tutor_id}",
    response_model=TutorProfileResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Профиль тутора (каталог)",
)
async def get_tutor(
    request: Request,
    tutor_id: UUID,
    tutor_filter: Annotated[TutorFilter, Depends()],
    users: Annotated[Users, Depends()],
    media: Annotated[Media, Depends()],
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
    profile_views: Annotated[AbstractTutorProfileViewService, Depends()],
) -> TutorProfileResponse | Response:
    try:
        profile = await tutor_filter.get(tutor_id)
    except TutorNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    await profile_views.record_view(request.state.user_id, tutor_id)
    user = await users.get_by_tutor_id(tutor_id)
    photo_key = user.photo if user is not None else None
    subscription_plan = None
    if user is not None:
        subscription_plan = await subscription_service.resolve_subscription_plan(
            user.id,
        )
    achievements: list[AchievementResponse] = []
    for achievement in profile.achievements:
        achievement_url = None
        if achievement.image:
            achievement_url = await media.url(achievement.image)
        achievements.append(
            AchievementResponse(
                image=achievement.image,
                url=achievement_url,
            )
        )
    video_url = None
    if profile.advantage.video:
        video_url = await media.url(profile.advantage.video)
    photo_url = None
    if photo_key:
        photo_url = await media.url(photo_key)
    return TutorProfileResponse(
        id=profile.id,
        description=profile.description,
        cities=profile.cities,
        levels=[level.value for level in profile.levels],
        price=profile.price,
        lesson_duration=profile.lesson_duration,
        work_format=profile.work_format.value,
        status=profile.status.value,
        photo_url=photo_url,
        subscription_plan=subscription_plan,
        achievements=achievements,
        advantage=AdvantageResponse(
            video=profile.advantage.video,
            video_url=video_url,
            points=[
                PointResponse(text=point.text) for point in profile.advantage.points
            ],
        ),
        contacts=[
            ContactResponse(name=contact.name, value=contact.value)
            for contact in profile.contacts
        ],
        tags=[TagResponse(name=tag.name) for tag in profile.tags],
    )
