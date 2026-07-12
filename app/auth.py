from hmac import compare_digest

from fastapi import HTTPException, Request, status

from app.settings import settings


def bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def token_matches(token: str | None, required: str | None) -> bool:
    return token is not None and required is not None and compare_digest(token, required)


async def require_admin_token(request: Request) -> None:
    required = settings.require_admin_token
    if not required:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FEEDWRIGHT_REQUIRE_ADMIN_TOKEN is not configured",
        )
    if not token_matches(bearer_token(request), required):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )
