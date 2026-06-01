from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    name: str


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1)
