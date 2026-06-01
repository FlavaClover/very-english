from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from api.schema import ErrorResponse
from api.tags.schema import TagCreateRequest, TagResponse
from core.tutors import AbstractTagsManager

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get(
    "",
    response_model=list[TagResponse],
    summary="Список тегов",
)
async def list_tags(
    tags_manager: Annotated[AbstractTagsManager, Depends()],
) -> list[TagResponse]:
    tags = await tags_manager.get_all()
    return [TagResponse(name=tag.name) for tag in tags]


@router.post(
    "",
    response_model=TagResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Создание тега (админ)",
)
async def create_tag(
    payload: TagCreateRequest,
    tags_manager: Annotated[AbstractTagsManager, Depends()],
) -> TagResponse | Response:
    try:
        await tags_manager.add(payload.name)
        tag = await tags_manager.get(payload.name)
    except ValueError as exc:
        return Response(
            content=ErrorResponse(detail=str(exc)).model_dump_json(),
            status_code=400,
            media_type="application/json",
        )
    return TagResponse(name=tag.name)


@router.delete(
    "/{tag_name}",
    status_code=204,
    summary="Удаление тега (админ)",
)
async def delete_tag(
    tag_name: str,
    tags_manager: Annotated[AbstractTagsManager, Depends()],
) -> None:
    try:
        await tags_manager.remove(tag_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
