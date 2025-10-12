from contextvars import ContextVar
from typing import Any

REQUEST_ID_CTX: ContextVar[str | None] = ContextVar("request_id", default=None)
ROUTE_CTX: ContextVar[str | None] = ContextVar("route", default=None)
CLIENT_IP_CTX: ContextVar[str | None] = ContextVar("client_ip", default=None)
REDIS_CTX: ContextVar[Any] = ContextVar("redis", default=None)
AUTH_USER_ID_CTX: ContextVar[int | None] = ContextVar("auth_user_id", default=None)
AUTH_ROLES_CTX: ContextVar[tuple[str, ...]] = ContextVar("auth_roles", default=())


def get_request_id() -> str | None:
    return REQUEST_ID_CTX.get()


def get_route() -> str | None:
    return ROUTE_CTX.get()


def get_client_ip() -> str | None:
    return CLIENT_IP_CTX.get()


def get_redis() -> Any:
    return REDIS_CTX.get()


def get_actor_id() -> int | None:
    return AUTH_USER_ID_CTX.get()


def get_actor_roles() -> tuple[str, ...]:
    return AUTH_ROLES_CTX.get()
