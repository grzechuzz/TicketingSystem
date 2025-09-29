import json
import time
from datetime import timezone, datetime
from fastapi import Request, HTTPException
from typing import Any, Mapping, Sequence
from app.core.ctx import REQUEST_ID_CTX
from app.core.config import AUDIT_STREAM
from app.domain.users.models import User
from sqlalchemy.exc import IntegrityError

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
) -> str | None:
    if request_id is None:
        request_id = REQUEST_ID_CTX.get()

    payload = {
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
    try:
        return await redis_db.xadd(stream, {"json": json.dumps(payload, default=str)})
    except Exception:
        return None


def roles_from_user(user: User) -> list[str]:
    return [r.name for r in user.roles]


def http_route_id(request: Request) -> str:
    return f"{request.method} {request.url.path}"


def client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else None)


async def audit_ok(r, **kwargs) -> str | None:
    return await audit_emit(r, status=AuditStatus.SUCCESS, **kwargs)


async def audit_fail(r, **kwargs) -> str | None:
    return await audit_emit(r, status=AuditStatus.FAIL, **kwargs)


def _reason_from_exception(exception: BaseException | None) -> str | None:
    if exception is None:
        return None

    try:
        if isinstance(exception, HTTPException):
            return str(exception.detail)
    except Exception:
        pass

    if isinstance(exception, IntegrityError):
        return "Integrity error"

    return str(exception)


class AuditSpan:
    def __init__(self, request, *, scope, action,
                 user=None, object_type=None, object_id=None,
                 organizer_id=None, event_id=None, order_id=None,
                 payment_id=None, invoice_id=None, meta=None):
        self.request = request
        self.scope = scope
        self.action = action
        self.user = user
        self.object_type = object_type
        self.object_id = object_id
        self.organizer_id = organizer_id
        self.event_id = event_id
        self.order_id = order_id
        self.payment_id = payment_id
        self.invoice_id = invoice_id
        self.meta = dict(meta or {})
        self._t0 = 0.0

    async def __aenter__(self):
        self._t0 = time.perf_counter()
        started = datetime.now(timezone.utc)
        self.meta.setdefault("occurred_at", started.isoformat(timespec="milliseconds").replace("+00:00", "Z"))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.meta["duration_ms"] = int((time.perf_counter() - self._t0) * 1000)
        actor_id = getattr(self.user, "id", None)
        actor_roles = roles_from_user(self.user) if self.user else []
        r = getattr(self.request.app.state, "redis", None)
        if not r:
            return False

        kwargs = dict(
            scope=self.scope,
            action=self.action,
            actor_user_id=actor_id,
            actor_roles=actor_roles,
            actor_ip=client_ip(self.request),
            route=http_route_id(self.request),
            object_type=self.object_type,
            object_id=self.object_id,
            organizer_id=self.organizer_id,
            event_id=self.event_id,
            order_id=self.order_id,
            payment_id=self.payment_id,
            invoice_id=self.invoice_id,
            meta=self.meta,
        )
        if exc:
            await audit_fail(r, reason=_reason_from_exception(exc), **kwargs)
            return False
        else:
            await audit_ok(r, **kwargs)
            return False
