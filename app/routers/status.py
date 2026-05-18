from fastapi import APIRouter
from pydantic import BaseModel

from app.settings import settings, Settings

router = APIRouter(prefix="/status", tags=["status"])


class ConfigurationResponse(BaseModel):
    settings: Settings


@router.get("/configuration", response_model=ConfigurationResponse)
async def get_configuration() -> ConfigurationResponse:
    return ConfigurationResponse(
        settings=settings,
    )
