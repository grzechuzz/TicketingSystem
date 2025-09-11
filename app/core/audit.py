import logging
from typing import Any, Sequence, Mapping
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, INET
from sqlalchemy import Text
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from app.core.ctx import REQUEST_ID_CTX


logger = logging.getLogger("app.audit")


class AuditStatus:
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


async def audit_log(
        db: AsyncSession,
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
        request_id: str | None = None
) -> None:
    if request_id is None:
        request_id = REQUEST_ID_CTX.get()
    if actor_roles is None:
        actor_roles = []
    if meta is None:
        meta = {}

    stmt = text("""
           INSERT INTO audit.audit_logs
           (request_id, scope, action, actor_user_id, actor_roles, actor_ip, route,
            object_type, object_id, organizer_id, event_id, order_id, payment_id,
            invoice_id, status, reason, meta)
           VALUES
           (:request_id, :scope, :action, :actor_user_id, :actor_roles, :actor_ip, :route,
            :object_type, :object_id, :organizer_id, :event_id, :order_id, :payment_id,
            :invoice_id, :status, :reason, :meta)
       """).bindparams(
        bindparam("actor_roles", type_=ARRAY(Text())),
        bindparam("actor_ip", type_=INET),
        bindparam("meta", type_=JSONB),
    )

    params = {
        "request_id": request_id,
        "scope": scope,
        "action": action,
        "actor_user_id": actor_user_id,
        "actor_roles": list(actor_roles),
        "actor_ip": actor_ip,
        "route": route,
        "object_type": object_type,
        "object_id": object_id,
        "organizer_id": organizer_id,
        "event_id": event_id,
        "order_id": order_id,
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "status": status,
        "reason": reason,
        "meta": dict(meta)
    }

    curr_transaction = db.get_transaction()
    try:
        if curr_transaction and curr_transaction.is_active:
            async with db.begin_nested():
                await db.execute(stmt, params)
        else:
            async with db.begin():
                await db.execute(stmt, params)

    except (DBAPIError, SQLAlchemyError):
        logger.exception(
            "Audit insert failed",
            extra={
                "scope": scope,
                "action": action,
                "status": status,
                "actor_user_id": actor_user_id,
                "request_id": request_id,
                "route": route
            }
        )


async def audit_ok(db: AsyncSession, **kwargs) -> None:
    await audit_log(db, status=AuditStatus.SUCCESS, **kwargs)


async def audit_fail(db: AsyncSession, **kwargs) -> None:
    await audit_log(db, status=AuditStatus.FAIL, **kwargs)


def roles_from_user(user) -> list[str]:
    return [r.name for r in (user.roles or [])]


def http_route_id(request) -> str:
    return f"{request.method} {request.url.path}"


def client_ip(request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else None)
