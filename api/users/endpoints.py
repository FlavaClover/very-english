from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from api.schema import ErrorResponse
from api.upload import save_upload_to_temp
from api.users.schema import (
    AutopaymentConsentRequest,
    UserResponse,
    UserUpdateRequest,
)
from auth.exceptions import UserNotFoundError
from auth.models import User
from auth.users import AbstractUserManager
from core.tutors import Media

router = APIRouter(prefix="/users", tags=["Users"])


async def _build_user_response(user: User, media: Media) -> UserResponse:
    photo = await media.url(user.photo) if user.photo else None
    return UserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role.value,
        photo=photo,
        autopayment_consent=user.autopayment_consent,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Текущий пользователь",
)
async def get_me(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    media: Annotated[Media, Depends()],
) -> UserResponse | Response:
    try:
        user = await user_manager.get(request.state.user_id)
    except UserNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return await _build_user_response(user, media)


@router.patch(
    "/me",
    response_model=UserResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Обновление профиля",
)
async def update_me(
    request: Request,
    payload: UserUpdateRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
    media: Annotated[Media, Depends()],
) -> UserResponse | Response:
    try:
        current = await user_manager.get(request.state.user_id)
        updated = await user_manager.update(
            request.state.user_id,
            User(
                id=current.id,
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=payload.email,
                role=current.role,
                photo=current.photo,
                autopayment_consent=current.autopayment_consent,
            ),
        )
    except UserNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return await _build_user_response(updated, media)


@router.patch(
    "/me/autopayment-consent",
    response_model=UserResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Согласие на автоплатежи",
)
async def update_autopayment_consent(
    request: Request,
    payload: AutopaymentConsentRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
    media: Annotated[Media, Depends()],
) -> UserResponse | Response:
    try:
        user = await user_manager.set_autopayment_consent(
            request.state.user_id,
            payload.consent,
        )
    except UserNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return await _build_user_response(user, media)


@router.post(
    "/me/photo",
    response_model=UserResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Загрузка фото профиля",
)
async def upload_photo(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    media: Annotated[Media, Depends()],
    file: UploadFile = File(...),
) -> UserResponse | Response:
    temp_path = await save_upload_to_temp(file)
    object_name = f"users/{request.state.user_id}/photo/{uuid4()}{temp_path.suffix}"
    try:
        user = await user_manager.set_photo(
            request.state.user_id,
            temp_path,
            object_name,
        )
    except UserNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    finally:
        temp_path.unlink(missing_ok=True)
    return await _build_user_response(user, media)


@router.delete(
    "/me/photo",
    response_model=UserResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Удаление фото профиля",
)
async def delete_photo(
    request: Request,
    user_manager: Annotated[AbstractUserManager, Depends()],
    media: Annotated[Media, Depends()],
) -> UserResponse | Response:
    try:
        user = await user_manager.remove_photo(request.state.user_id)
    except UserNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=404,
            media_type="application/json",
        )
    return await _build_user_response(user, media)
