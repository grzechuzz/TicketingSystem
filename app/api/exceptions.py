from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.domain.exceptions import AppError, NotFound, Conflict, Unprocessable, Unauthorized, InvalidInput, Forbidden
from app.core.ctx import REQUEST_ID_CTX

MEDIA_TYPE = "application/problem+json"

_STATUS_BY_CLASS: dict[type[AppError], int] = {
    NotFound: status.HTTP_404_NOT_FOUND,
    Unauthorized: status.HTTP_401_UNAUTHORIZED,
    Forbidden: status.HTTP_403_FORBIDDEN,
    Conflict: status.HTTP_409_CONFLICT,
    InvalidInput: status.HTTP_400_BAD_REQUEST,
    Unprocessable: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AppError: status.HTTP_400_BAD_REQUEST,
}

_TITLES: dict[type[AppError], str] = {
    NotFound: "Not Found",
    Unauthorized: "Unauthorized",
    Forbidden: "Forbidden",
    Conflict: "Conflict",
    InvalidInput: "Bad Request",
    Unprocessable: "Unprocessable Entity",
    AppError: "Application Error",
}

def _www_authenticate_header(
        scheme: str = "Bearer",
        realm: str | None = "api",
        error: str | None = "invalid_token",
        error_description: str | None = None,
) -> str:
    parts = [scheme]
    attributes = []
    if realm:
        attributes.append(f'realm="{realm}"')
    if error:
        attributes.append(f'error="{error}"')
    if error_description:
        attributes.append(f'error_description="{error_description}"')
    if attributes:
        parts.append(" " + ", ".join(attributes))
    return "".join(parts)


def _status_for(exc: AppError) -> int:
    for cls in type(exc).mro():
        if cls in _STATUS_BY_CLASS:
            return _STATUS_BY_CLASS[cls]
    return status.HTTP_400_BAD_REQUEST


def _title_for(exc: AppError) -> str:
    for cls in type(exc).mro():
        if cls in _TITLES:
            return _TITLES[cls]
    return "Application Error"


def _problem(
    request: Request,
    *,
    http_status: int,
    title: str,
    detail: str | None = None,
    extra: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = {
        "status": http_status,
        "title": title,
        "detail": detail,
        "instance": str(request.url),
    }
    req_id = REQUEST_ID_CTX.get()
    if req_id:
        body["trace_id"] = req_id
    if extra:
        body.update({k: v for k, v in extra.items() if v is not None})
    return JSONResponse(status_code=http_status, content=body, media_type=MEDIA_TYPE, headers=headers or {})


def register_error_handler(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError):
        status_code = _status_for(exc)
        title = _title_for(exc)
        detail = str(exc) or None
        extra = {"context": getattr(exc, "ctx", None)} if getattr(exc, "ctx", None) else None

        headers: dict[str, str] | None = None
        if isinstance(exc, Unauthorized):
            headers = {
                "WWW-Authenticate": _www_authenticate_header(
                    scheme="Bearer", realm="api", error="invalid_token", error_description=detail
                )
            }

        return _problem(
            request,
            http_status=status_code,
            title=title,
            detail=detail,
            extra=extra,
            headers=headers
        )
