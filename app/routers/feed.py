from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ValidationError

from app.extract import extractors
from app.render import OutputFormat
from app.settings import settings, Settings

router = APIRouter(prefix="/feed", tags=["status"])


class GetFeedsResponse(BaseModel):
    feeds: list[str]


@router.get("/", response_model=GetFeedsResponse)
async def get_feeds() -> GetFeedsResponse:
    return GetFeedsResponse(
        feeds=sorted(list(extractors.extractors)),
    )


@router.get("/{name}/view/{format}")
async def get_feed(name: str, format: OutputFormat):

    try:
        feed = await extractors.get(name)
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid feed configuration or response",
                "details": e.errors(),
            },
        )

    return format.render_response(feed)
