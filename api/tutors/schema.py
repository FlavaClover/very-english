from uuid import UUID

from pydantic import BaseModel, Field

from billing.subscriptions import SubscriptionPlanId
from core.models import PriceSort


class ContactRequest(BaseModel):
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)


class ContactResponse(BaseModel):
    name: str
    value: str


class TagResponse(BaseModel):
    name: str


class AchievementResponse(BaseModel):
    image: str
    url: str | None = None


class MediaUrlResponse(BaseModel):
    url: str


class AchievementUrlItemResponse(BaseModel):
    image: str
    url: str


class PointResponse(BaseModel):
    text: str


class AdvantageResponse(BaseModel):
    video: str
    video_url: str | None = None
    points: list[PointResponse]


class TutorResponse(BaseModel):
    id: UUID
    description: str
    cities: list[str]
    levels: list[str]
    price: int
    lesson_duration: int
    work_format: str


class TutorProfileResponse(TutorResponse):
    status: str
    photo_url: str | None = None
    subscription_plan: SubscriptionPlanId | None = None
    achievements: list[AchievementResponse]
    advantage: AdvantageResponse
    contacts: list[ContactResponse]
    tags: list[TagResponse]


class TutorProfileCreateRequest(BaseModel):
    description: str = Field(min_length=1)
    cities: list[str] = Field(min_length=1)
    levels: list[str] = Field(min_length=1)
    price: int = Field(gt=0)
    lesson_duration: int = Field(gt=0)
    work_format: str
    contacts: list[ContactRequest] = Field(min_length=1)
    tags: list[str] = Field(min_length=1)


class TutorProfileUpdateRequest(BaseModel):
    description: str = Field(min_length=1)
    cities: list[str] = Field(min_length=1)
    levels: list[str] = Field(min_length=1)
    price: int = Field(gt=0)
    lesson_duration: int = Field(gt=0)
    work_format: str


class TutorListQuery(BaseModel):
    price_from: int | None = None
    price_to: int | None = None
    levels: list[str] | None = None
    work_formats: list[str] | None = None
    cities: list[str] | None = None
    tags: list[str] | None = None
    price_sort: PriceSort | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
