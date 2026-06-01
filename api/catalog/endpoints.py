from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from api.schema import ErrorResponse
from api.tutors.schema import (
    AchievementResponse,
    AchievementUrlItemResponse,
    AdvantageResponse,
    ContactResponse,
    MediaUrlResponse,
    PointResponse,
    TagResponse,
    TutorProfileResponse,
)
from auth.users import Users
from core.exceptions import TutorNotFoundError
from core.models import Level, Tag, TutorProfile, TutorStatus, WorkFormat
from core.tutors import Media, TutorFilter

router = APIRouter(prefix="/tutors", tags=["Catalog"])


async def _load_approved_profile(
    tutor_id: UUID,
    tutor_filter: TutorFilter,
) -> TutorProfile | Response:
    try:
        profile = await tutor_filter.get(tutor_id)
    except TutorNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    if profile.status is not TutorStatus.APPROVED:
        return Response(
            content=ErrorResponse(detail="Tutor not found").model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return profile


@router.get(
    "",
    response_model=list[TutorProfileResponse],
    summary="Список туторов (каталог)",
)
async def list_tutors(
    tutor_filter: Annotated[TutorFilter, Depends()],
    price_from: int | None = Query(default=None, ge=0),
    price_to: int | None = Query(default=None, ge=0),
    levels: list[str] | None = Query(default=None),
    work_formats: list[str] | None = Query(default=None),
    cities: list[str] | None = Query(default=None),
    tags: list[str] | None = Query(default=None),
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
        page=page,
        page_size=page_size,
    )
    return [
        TutorProfileResponse(
            id=profile.id,
            description=profile.description,
            cities=profile.cities,
            levels=[level.value for level in profile.levels],
            price=profile.price,
            lesson_duration=profile.lesson_duration,
            work_format=profile.work_format.value,
            status=profile.status.value,
            achievements=[
                AchievementResponse(image=achievement.image)
                for achievement in profile.achievements
            ],
            advantage=AdvantageResponse(
                video=profile.advantage.video,
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
        for profile in profiles
    ]


@router.get(
    "/{tutor_id}",
    response_model=TutorProfileResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Профиль тутора (каталог)",
)
async def get_tutor(
    tutor_id: UUID,
    tutor_filter: Annotated[TutorFilter, Depends()],
) -> TutorProfileResponse | Response:
    try:
        profile = await tutor_filter.get(tutor_id)
    except TutorNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return TutorProfileResponse(
        id=profile.id,
        description=profile.description,
        cities=profile.cities,
        levels=[level.value for level in profile.levels],
        price=profile.price,
        lesson_duration=profile.lesson_duration,
        work_format=profile.work_format.value,
        status=profile.status.value,
        achievements=[
            AchievementResponse(image=achievement.image)
            for achievement in profile.achievements
        ],
        advantage=AdvantageResponse(
            video=profile.advantage.video,
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


@router.get(
    "/{tutor_id}/photo/url",
    response_model=MediaUrlResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Ссылка на аватар тутора (каталог)",
)
async def get_tutor_photo_url(
    tutor_id: UUID,
    tutor_filter: Annotated[TutorFilter, Depends()],
    users: Annotated[Users, Depends()],
    media: Annotated[Media, Depends()],
) -> MediaUrlResponse | Response:
    profile = await _load_approved_profile(tutor_id, tutor_filter)
    if isinstance(profile, Response):
        return profile
    user = await users.get_by_tutor_id(tutor_id)
    if user is None or user.photo is None:
        return Response(
            content=ErrorResponse(detail="Photo is not set").model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    url = await media.url(user.photo)
    return MediaUrlResponse(url=url)


@router.get(
    "/{tutor_id}/visit-video/url",
    response_model=MediaUrlResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Ссылка на видео-визитку тутора (каталог)",
)
async def get_tutor_visit_video_url(
    tutor_id: UUID,
    tutor_filter: Annotated[TutorFilter, Depends()],
    media: Annotated[Media, Depends()],
) -> MediaUrlResponse | Response:
    profile = await _load_approved_profile(tutor_id, tutor_filter)
    if isinstance(profile, Response):
        return profile
    if not profile.advantage.video:
        return Response(
            content=ErrorResponse(detail="Visit video is not set").model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    url = await media.url(profile.advantage.video)
    return MediaUrlResponse(url=url)


@router.get(
    "/{tutor_id}/achievements/urls",
    response_model=list[AchievementUrlItemResponse],
    responses={404: {"model": ErrorResponse}},
    summary="Ссылки на достижения тутора (каталог)",
)
async def get_tutor_achievement_urls(
    tutor_id: UUID,
    tutor_filter: Annotated[TutorFilter, Depends()],
    media: Annotated[Media, Depends()],
) -> list[AchievementUrlItemResponse] | Response:
    profile = await _load_approved_profile(tutor_id, tutor_filter)
    if isinstance(profile, Response):
        return profile
    items: list[AchievementUrlItemResponse] = []
    for achievement in profile.achievements:
        items.append(
            AchievementUrlItemResponse(
                image=achievement.image,
                url=await media.url(achievement.image),
            )
        )
    return items
