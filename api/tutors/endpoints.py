import json
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)

from api.schema import ErrorResponse
from api.upload import save_upload_to_temp
from api.tutors.schema import (
    AchievementResponse,
    AdvantageResponse,
    ContactRequest,
    ContactResponse,
    PointResponse,
    TagResponse,
    TutorProfileCreateRequest,
    TutorProfileResponse,
    TutorProfileUpdateRequest,
    TutorResponse,
)
from auth.users import AbstractUserManager
from core.exceptions import TutorNotFoundError
from core.models import Contact, Level, Point, Tag, Tutor, TutorStatus, WorkFormat
from core.tutors import AbstractTutorManager, Media, TutorFilter

router = APIRouter(prefix="/tutors", tags=["Tutors"])


async def _get_linked_tutor_id(
    request: Request,
    user_manager: AbstractUserManager,
) -> UUID | Response:
    tutor_id = await user_manager.get_tutor_id(request.state.user_id)
    if tutor_id is None:
        return Response(
            content=ErrorResponse(
                detail="Tutor profile is not linked to this user"
            ).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return tutor_id


@router.post(
    "/profile",
    response_model=TutorResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Создание профиля тутора",
)
async def create_profile(
    request: Request,
    payload: TutorProfileCreateRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> TutorResponse | Response:
    existing = await user_manager.get_tutor_id(request.state.user_id)
    if existing is not None:
        return Response(
            content=ErrorResponse(
                detail="Tutor profile already exists"
            ).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    try:
        tutor = await tutor_manager.create(
            description=payload.description,
            cities=payload.cities,
            levels=[Level(level) for level in payload.levels],
            price=payload.price,
            lesson_duration=payload.lesson_duration,
            work_format=WorkFormat(payload.work_format),
            contacts=[
                Contact(name=contact.name, value=contact.value)
                for contact in payload.contacts
            ],
            tags=[Tag(name=name) for name in payload.tags],
        )
        await user_manager.link_tutor_profile(request.state.user_id, tutor.id)
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
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


@router.get(
    "/me/profile",
    response_model=TutorProfileResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Свой профиль тутора",
)
async def get_my_profile(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_filter: Annotated[TutorFilter, Depends()],
    media: Annotated[Media, Depends()],
) -> TutorProfileResponse | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    try:
        profile = await tutor_filter.get(tutor_id)
    except TutorNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    achievements: list[AchievementResponse] = []
    for achievement in profile.achievements:
        achievements.append(
            AchievementResponse(
                image=achievement.image,
                url=await media.url(achievement.image),
            )
        )
    video_url = None
    if profile.advantage.video:
        video_url = await media.url(profile.advantage.video)
    return TutorProfileResponse(
        id=profile.id,
        description=profile.description,
        cities=profile.cities,
        levels=[level.value for level in profile.levels],
        price=profile.price,
        lesson_duration=profile.lesson_duration,
        work_format=profile.work_format.value,
        status=profile.status.value,
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


@router.patch(
    "/me/profile",
    response_model=TutorResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Редактирование профиля тутора",
)
async def update_my_profile(
    request: Request,
    payload: TutorProfileUpdateRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> TutorResponse | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    try:
        updated = Tutor(
            id=tutor_id,
            description=payload.description,
            cities=payload.cities,
            levels=[Level(level) for level in payload.levels],
            price=payload.price,
            lesson_duration=payload.lesson_duration,
            work_format=WorkFormat(payload.work_format),
        )
        tutor = await tutor_manager.update(tutor_id, updated)
    except (TutorNotFoundError, ValueError) as exc:
        status = 404 if isinstance(exc, TutorNotFoundError) else 400
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=status,
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
    "/me/submit-moderation",
    response_model=TutorResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Отправка профиля на модерацию",
)
async def submit_moderation(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> TutorResponse | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    try:
        tutor = await tutor_manager.set_status(tutor_id, TutorStatus.MODERATION)
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
    "/me/contacts",
    response_model=TutorResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Добавление способа связи",
)
async def add_contact(
    request: Request,
    payload: ContactRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> TutorResponse | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    try:
        tutor = await tutor_manager.add_contact(
            tutor_id,
            payload.name,
            payload.value,
        )
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
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


@router.delete(
    "/me/contacts/{contact_name}",
    response_model=TutorResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Удаление способа связи",
)
async def remove_contact(
    request: Request,
    contact_name: str,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> TutorResponse | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    try:
        tutor = await tutor_manager.remove_contact(tutor_id, contact_name)
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
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
    "/me/tags/{tag_name}",
    status_code=204,
    summary="Привязка тега к профилю",
)
async def link_tag(
    request: Request,
    tag_name: str,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> None:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        raise HTTPException(status_code=404, detail="Tutor profile is not linked")
    try:
        await tutor_manager.link_tag_to_tutor(tutor_id, tag_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/me/tags/{tag_name}",
    status_code=204,
    summary="Отвязка тега от профиля",
)
async def unlink_tag(
    request: Request,
    tag_name: str,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> None:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        raise HTTPException(status_code=404, detail="Tutor profile is not linked")
    try:
        await tutor_manager.unlink_tag_from_tutor(tutor_id, tag_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/me/achievements",
    response_model=dict,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Загрузка достижения",
)
async def upload_achievement(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
    file: UploadFile = File(...),
) -> dict | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    temp_path = await save_upload_to_temp(file)
    object_name = f"tutors/{tutor_id}/achievements/{uuid4()}{temp_path.suffix}"
    try:
        achievement = await tutor_manager.add_achievement(
            tutor_id,
            temp_path,
            object_name,
        )
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    finally:
        temp_path.unlink(missing_ok=True)
    return {"image": achievement.image}


@router.delete(
    "/me/achievements/{achievement_name}",
    status_code=204,
    summary="Удаление достижения",
)
async def delete_achievement(
    request: Request,
    achievement_name: str,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> None:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        raise HTTPException(status_code=404, detail="Tutor profile is not linked")
    try:
        await tutor_manager.remove_achievement(tutor_id, achievement_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/me/visit-video",
    response_model=dict,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Загрузка видео-визитки",
)
async def upload_visit_video(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
    file: UploadFile = File(...),
) -> dict | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    temp_path = await save_upload_to_temp(file)
    object_name = f"tutors/{tutor_id}/visit/{uuid4()}{temp_path.suffix}"
    try:
        advantage = await tutor_manager.upload_visit_video(
            tutor_id,
            temp_path,
            object_name,
        )
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    finally:
        temp_path.unlink(missing_ok=True)
    return {"video": advantage.video, "points": [p.text for p in advantage.points]}


@router.post(
    "/me/advantage",
    response_model=dict,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Загрузка преимуществ (видео и пункты)",
)
async def upload_advantage(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
    file: UploadFile = File(...),
    points: str = Form(..., description="JSON-массив строк с текстом пунктов"),
) -> dict | Response:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        return tutor_id
    try:
        point_texts = json.loads(points)
        if not isinstance(point_texts, list):
            raise ValueError("points must be a JSON array of strings")
        parsed_points = [Point(text=str(text)) for text in point_texts]
    except (json.JSONDecodeError, ValueError) as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    temp_path = await save_upload_to_temp(file)
    object_name = f"tutors/{tutor_id}/advantage/{uuid4()}{temp_path.suffix}"
    try:
        advantage = await tutor_manager.set_advantage(
            tutor_id,
            parsed_points,
            temp_path,
            object_name,
        )
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    finally:
        temp_path.unlink(missing_ok=True)
    return {"video": advantage.video, "points": [p.text for p in advantage.points]}


@router.delete(
    "/me/advantage",
    status_code=204,
    summary="Удаление блока преимуществ",
)
async def delete_advantage(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> None:
    tutor_id = await _get_linked_tutor_id(request, user_manager)
    if isinstance(tutor_id, Response):
        raise HTTPException(status_code=404, detail="Tutor profile is not linked")
    try:
        await tutor_manager.remove_advantage(tutor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
