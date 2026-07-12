from collections.abc import Callable, Awaitable
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.ai import AI_AVAILABLE
from app.auth import bearer_token, token_matches
from app.settings import settings

from app.routers.feed import router as feed_router
from app.routers.status import router as status_router


from app import __version__ as app_version

app = FastAPI(title="Feedwright", version=app_version)

app.include_router(feed_router)
app.include_router(status_router)

if AI_AVAILABLE:
    from app.routers.autoconfigure import router as autoconfigure_router

    app.include_router(autoconfigure_router)


@app.middleware("http")
async def require_token_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]
) -> JSONResponse:
    """Require a token for all requests when settings.require_token is set.

    Token may be supplied either as an Authorization: Bearer <token>
    header, or as a query parameter named `token`.
    """
    required = settings.require_token
    # Allow unauthenticated access to API documentation and OpenAPI spec
    path = request.url.path
    if required and not (
        path.startswith("/docs")
        or path.startswith("/redoc")
        or path == "/openapi.json"
        or path == "/openapi.yaml"
    ):
        token = bearer_token(request)

        # Fallback to query parameter
        if token is None:
            token = request.query_params.get("token")

        if not token_matches(token, required) and not token_matches(
            token, settings.require_admin_token
        ):
            return JSONResponse({"detail": "Invalid or missing token"}, status_code=401)

    return await call_next(request)
