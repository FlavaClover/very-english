from typing import Annotated

from fastapi import APIRouter, Depends, Response

from api.auth.schema import (
    SendEmailCodeRequest,
    VerifyEmailRequest,
    VerifyEmailResponse,
    VkIdLoginRequest,
)
from api.schema import ErrorResponse
from api.users.schema import (
    RefreshTokenRequest,
    TokenPairResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from auth.exceptions import (
    EmailAlreadyRegisteredError,
    EmailVerificationMismatchError,
    EmailVerificationNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    InvalidVerificationCodeError,
    UserAlreadyExistsError,
    UserNotFoundError,
    VkIdAuthError,
)
from auth.models import UserRole
from auth.users import AbstractUserManager
from auth.email_verification import AbstractEmailVerificationService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/send-code",
    status_code=204,
    responses={400: {"model": ErrorResponse}},
    summary="Отправить код подтверждения на email",
)
async def send_email_code(
    payload: SendEmailCodeRequest,
    email_verification_service: Annotated[AbstractEmailVerificationService, Depends()],
) -> Response:
    try:
        await email_verification_service.send_code(payload.email)
    except EmailAlreadyRegisteredError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    return Response(status_code=204)


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Подтвердить email по коду",
)
async def verify_email(
    payload: VerifyEmailRequest,
    email_verification_service: Annotated[AbstractEmailVerificationService, Depends()],
) -> VerifyEmailResponse | Response:
    try:
        verification_id = await email_verification_service.verify_email(
            payload.email,
            payload.code,
        )
    except InvalidVerificationCodeError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    return VerifyEmailResponse(email_verification_id=verification_id)


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
            email_verification_id=payload.email_verification_id,
        )
    except UserAlreadyExistsError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except EmailVerificationNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except EmailVerificationMismatchError as exc:
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
    summary="Регистрация тутора",
)
async def register_tutor(
    payload: UserRegisterRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
) -> UserResponse | Response:
    try:
        user = await user_manager.register(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password=payload.password,
            email_verification_id=payload.email_verification_id,
            role=UserRole.TUTOR,
        )
    except UserAlreadyExistsError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except EmailVerificationNotFoundError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    except EmailVerificationMismatchError as exc:
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
    "/login/vkid",
    response_model=TokenPairResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Вход через VK ID",
)
async def login_vkid(
    payload: VkIdLoginRequest,
    user_manager: Annotated[AbstractUserManager, Depends()],
) -> TokenPairResponse | Response:
    try:
        _, tokens = await user_manager.login_vkid(
            code=payload.code,
            state=payload.state,
            code_verifier=payload.code_verifier,
            device_id=payload.device_id,
        )
    except VkIdAuthError as exc:
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
