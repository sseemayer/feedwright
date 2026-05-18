from collections.abc import Callable, Awaitable
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.settings import settings

from app.routers.feed import router as feed_router
from app.routers.status import router as status_router

app = FastAPI()

app.include_router(feed_router)
app.include_router(status_router)


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
        # Check Authorization header first
        auth = request.headers.get("authorization")
        token = None
        if auth:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

        # Fallback to query parameter
        if token is None:
            token = request.query_params.get("token")

        if token != required:
            return JSONResponse({"detail": "Invalid or missing token"}, status_code=401)

    return await call_next(request)
