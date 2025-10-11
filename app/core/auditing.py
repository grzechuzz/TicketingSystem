import json
import time
from datetime import timezone, datetime
from typing import Any, Mapping
from app.core.config import AUDIT_STREAM
from app.core.ctx import get_redis, get_request_id, get_route, get_actor_id, get_actor_roles, get_client_ip
from sqlalchemy.exc import IntegrityError


class AuditStatus:
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


async def audit_emit(
    *,
    scope: str,
    action: str,
    status: str,
    object_type: str | None = None,
    object_id: int | None = None,
    organizer_id: int | None = None,
    event_id: int | None = None,
    order_id: int | None = None,
    payment_id: int | None = None,
    invoice_id: int | None = None,
    reason: str | None = None,
    meta: Mapping[str, Any] | None = None
) -> str | None:
    r = get_redis()
    if not r:
        return None

    payload = {
        "request_id": get_request_id(),
        "scope": scope,
        "action": action,
        "status": status,
        "actor_user_id": get_actor_id(),
        "actor_roles": list(get_actor_roles() or []),
        "actor_ip": get_client_ip(),
        "route": get_route(),
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
        return await r.xadd(AUDIT_STREAM, {"json": json.dumps(payload, default=str)})
    except Exception:
        return None


def _reason_from_exception(exception: BaseException | None) -> str | None:
    if exception is None:
        return None
    try:
        from fastapi import HTTPException
        if isinstance(exception, HTTPException):
            return str(exception.detail)
    except Exception:
        pass
    if isinstance(exception, IntegrityError):
        return "Integrity error"
    return str(exception)


class AuditSpan:
    def __init__(self, *, scope: str, action: str,
                 object_type: str | None = None, object_id: int | None = None,
                 organizer_id: int | None = None, event_id: int | None = None,
                 order_id: int | None = None, payment_id: int | None = None,
                 invoice_id: int | None = None, meta: Mapping[str, Any] | None = None):
        self.scope = scope
        self.action = action
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
        status = AuditStatus.FAIL if exc else AuditStatus.SUCCESS
        await audit_emit(
            scope=self.scope, action=self.action, status=status,
            object_type=self.object_type, object_id=self.object_id,
            organizer_id=self.organizer_id, event_id=self.event_id,
            order_id=self.order_id, payment_id=self.payment_id, invoice_id=self.invoice_id,
            reason=_reason_from_exception(exc), meta=self.meta
        )
        return False
