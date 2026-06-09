from pydantic import BaseModel, Field


class VkIdLoginRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)
    code_verifier: str = Field(min_length=43, max_length=128)
    device_id: str = Field(min_length=1)
