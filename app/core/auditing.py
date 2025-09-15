import json
from datetime import timezone, datetime
from fastapi import Request
from typing import Any, Mapping, Sequence
from app.core.ctx import REQUEST_ID_CTX
from app.core.config import AUDIT_STREAM
from app.domain.users.models import User


class AuditStatus:
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


async def audit_emit(
    redis_db,
    *,
    scope: str,
    action: str,
    status: str,
    actor_user_id: int | None = None,
    actor_roles: Sequence[str] | None = None,
    actor_ip: str | None = None,
    route: str | None = None,
    object_type: str | None = None,
    object_id: int | None = None,
    organizer_id: int | None = None,
    event_id: int | None = None,
    order_id: int | None = None,
    payment_id: int | None = None,
    invoice_id: int | None = None,
    reason: str | None = None,
    meta: Mapping[str, Any] | None = None,
    request_id: str | None = None,
    stream: str = AUDIT_STREAM,
) -> str:
    if request_id is None:
        request_id = REQUEST_ID_CTX.get()

    payload = {
        "created_at": datetime.now(timezone.utc),
        "request_id": request_id,
        "scope": scope,
        "action": action,
        "status": status,
        "actor_user_id": actor_user_id,
        "actor_roles": list(actor_roles or []),
        "actor_ip": actor_ip,
        "route": route,
        "object_type": object_type,
        "object_id": object_id,
        "organizer_id": organizer_id,
        "event_id": event_id,
        "order_id": order_id,
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "reason": reason,
        "meta": dict(meta or {}),
    }

    return await redis_db.xadd(stream, {"json": json.dumps(payload, default=str)})


def roles_from_user(user: User) -> list[str]:
    return [r.name for r in user.roles]


def http_route_id(request: Request) -> str:
    return f"{request.method} {request.url.path}"


def client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else None)


async def audit_ok(r, **kwargs) -> str:
    return await audit_emit(r, status=AuditStatus.SUCCESS, **kwargs)


async def audit_fail(r, **kwargs) -> str:
    return await audit_emit(r, status=AuditStatus.FAIL, **kwargs)
