from uuid import UUID


from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    role: str
    photo: str | None = None
    autopayment_consent: bool = False


class AutopaymentConsentRequest(BaseModel):
    consent: bool


class UserRegisterRequest(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    email_verification_id: UUID


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserUpdateRequest(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = Field(min_length=3)
