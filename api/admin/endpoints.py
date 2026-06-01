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
from core.exceptions import TutorNotFoundError
from core.models import TutorStatus
from core.tutors import AbstractTutorManager, TutorFilter

router = APIRouter(prefix="/admin/tutors", tags=["Admin"])


@router.get(
    "/moderation",
    response_model=list[TutorProfileResponse],
    summary="Профили на модерации",
)
async def list_for_moderation(
    tutor_filter: Annotated[TutorFilter, Depends()],
) -> list[TutorProfileResponse]:
    profiles = await tutor_filter.for_moderation()
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
