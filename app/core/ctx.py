from contextvars import ContextVar

REQUEST_ID_CTX: ContextVar[str | None] = ContextVar("request_id", default=None)
