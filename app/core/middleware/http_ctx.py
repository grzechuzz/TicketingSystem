from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.ctx import REQUEST_ID_CTX, ROUTE_CTX, CLIENT_IP_CTX, REDIS_CTX


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else None)


def _http_route(request: Request) -> str:
    return f"{request.method} {request.url.path}"


class HttpContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, request_id_header: str = "X-Request-ID"):
        super().__init__(app)
        self.request_id_header = request_id_header

    async def dispatch(self, request: Request, call_next):
        tokens: list[tuple] = []
        try:
            req_id = request.headers.get(self.request_id_header)
            if req_id is not None:
                tokens.append((REQUEST_ID_CTX, REQUEST_ID_CTX.set(req_id)))

            tokens.append((ROUTE_CTX, ROUTE_CTX.set(_http_route(request))))
            tokens.append((CLIENT_IP_CTX, CLIENT_IP_CTX.set(_client_ip(request))))

            redis_client = getattr(request.app.state, "redis", None)
            if redis_client:
                tokens.append((REDIS_CTX, REDIS_CTX.set(redis_client)))

            return await call_next(request)
        finally:
            for var, token in reversed(tokens):
                var.reset(token)
