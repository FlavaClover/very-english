from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from api.schema import ErrorResponse
from api.tutors.schema import (
    AchievementResponse,
    AdvantageResponse,
    ContactResponse,
    PointResponse,
    TagResponse,
    TutorProfileResponse,
    TutorResponse,
)
from auth.users import Users
from core.exceptions import TutorNotFoundError
from core.models import TutorStatus
from core.tutors import Media, TutorFilter
from services.subscription import AbstractSubscriptionService
from services.tutors import AbstractTutorManager

router = APIRouter(prefix="/admin/tutors", tags=["Admin"])


@router.get(
    "/moderation",
    response_model=list[TutorProfileResponse],
    summary="Профили на модерации",
)
async def list_for_moderation(
    tutor_filter: Annotated[TutorFilter, Depends()],
    users: Annotated[Users, Depends()],
    media: Annotated[Media, Depends()],
    subscription_service: Annotated[AbstractSubscriptionService, Depends()],
) -> list[TutorProfileResponse]:
    profiles = await tutor_filter.for_moderation()
    result: list[TutorProfileResponse] = []
    for profile in profiles:
        user = await users.get_by_tutor_id(profile.id)
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
        photo_key = user.photo if user is not None else None
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


@router.post(
    "/{tutor_id}/approve",
    response_model=TutorResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Одобрение профиля",
)
async def approve_tutor(
    tutor_id: UUID,
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> TutorResponse | Response:
    try:
        tutor = await tutor_manager.set_status(tutor_id, TutorStatus.APPROVED)
    except TutorNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return TutorResponse(
        id=tutor.id,
        description=tutor.description,
        cities=tutor.cities,
        levels=[level.value for level in tutor.levels],
        price=tutor.price,
        lesson_duration=tutor.lesson_duration,
        work_format=tutor.work_format.value,
    )


@router.post(
    "/{tutor_id}/reject",
    response_model=TutorResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Возврат профиля в черновик",
)
async def reject_tutor(
    tutor_id: UUID,
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> TutorResponse | Response:
    try:
        tutor = await tutor_manager.set_status(tutor_id, TutorStatus.DRAFT)
    except TutorNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return TutorResponse(
        id=tutor.id,
        description=tutor.description,
        cities=tutor.cities,
        levels=[level.value for level in tutor.levels],
        price=tutor.price,
        lesson_duration=tutor.lesson_duration,
        work_format=tutor.work_format.value,
    )
