from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_admin_token
from app.autoconfigure import (
    AiConfigurationError,
    AutoConfigureRequest,
    AutoConfigureResult,
    InvalidPluginError,
    ProviderError,
    SourceFetchError,
    ValidationExhaustedError,
    autoconfigure,
)


router = APIRouter(prefix="/feed", tags=["Feed auto-configuration"])


@router.post(
    "/generate-config",
    response_model=AutoConfigureResult,
    dependencies=[Depends(require_admin_token)],
)
async def generate_config(request: AutoConfigureRequest) -> AutoConfigureResult:
    try:
        return await autoconfigure(request)
    except InvalidPluginError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AiConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except (SourceFetchError, ProviderError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValidationExhaustedError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "validation_exhausted",
                "message": str(exc),
                "attempts": [report.model_dump(mode="json") for report in exc.reports],
            },
        ) from exc
