import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.ctx import REQUEST_ID_CTX


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request, call_next):
        rid = request.headers.get(self.header_name) or str(uuid.uuid4())
        token = REQUEST_ID_CTX.set(rid)
        try:
            response = await call_next(request)
            response.headers.setdefault(self.header_name, rid)
            return response
        finally:
            REQUEST_ID_CTX.reset(token)
