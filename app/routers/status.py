from fastapi import APIRouter

from app.settings import settings, Settings

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/configuration", response_model=Settings)
async def get_configuration():
    return settings
