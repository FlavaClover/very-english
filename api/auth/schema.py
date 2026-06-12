from uuid import UUID

from pydantic import BaseModel, Field


class SendEmailCodeRequest(BaseModel):
    email: str = Field(min_length=3)


class VerifyEmailRequest(BaseModel):
    email: str = Field(min_length=3)
    code: str = Field(min_length=4, max_length=10)


class VerifyEmailResponse(BaseModel):
    email_verification_id: UUID


class VkIdLoginRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)
    code_verifier: str = Field(min_length=43, max_length=128)
    device_id: str = Field(min_length=1)
