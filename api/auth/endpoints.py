from typing import Annotated

from fastapi import APIRouter, Depends, Response

from api.schema import ErrorResponse
from api.users.schema import (
    RefreshTokenRequest,
    TokenPairResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from auth.users import AbstractUserManager
from api.tutors.schema import TutorRegisterRequest
from core.models import Contact, Level, Tag, WorkFormat
from core.tutors import AbstractTutorManager

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Регистрация пользователя",
)
async def register_user(
    payload: UserRegisterRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
) -> UserResponse | Response:
    try:
        user = await user_manager.register(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password=payload.password,
        )
    except UserAlreadyExistsError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    return UserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role.value,
        photo=user.photo,
    )


@router.post(
    "/register/tutor",
    response_model=UserResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Регистрация тутора с профилем",
)
async def register_tutor(
    payload: TutorRegisterRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
    tutor_manager: Annotated[AbstractTutorManager, Depends()],
) -> UserResponse | Response:
    from auth.models import UserRole

    try:
        user = await user_manager.register(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password=payload.password,
            role=UserRole.TUTOR,
        )
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
        await user_manager.link_tutor_profile(user.id, tutor.id)
    except UserAlreadyExistsError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    return UserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role.value,
        photo=user.photo,
    )


@router.post(
    "/login",
    response_model=TokenPairResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Вход",
)
async def login(
    payload: UserLoginRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
) -> TokenPairResponse | Response:
    try:
        _, tokens = await user_manager.login(
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=401,
            media_type="application/json",
        )
    return TokenPairResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Обновление токенов",
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
) -> TokenPairResponse | Response:
    try:
        tokens = await user_manager.refresh(payload.refresh_token)
    except (InvalidTokenError, UserNotFoundError) as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=401,
            media_type="application/json",
        )
    return TokenPairResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )
