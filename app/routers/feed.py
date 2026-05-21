from fastapi import APIRouter
from pydantic import BaseModel

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
    feed = await extractors.get(name)
    return format.render_response(feed)
