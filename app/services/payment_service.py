from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.payments import crud
from app.domain.payments.models import PaymentMethod, Payment, PaymentStatus
from app.domain.payments.schemas import PaymentMethodCreateDTO, PaymentMethodUpdateDTO, PaymentCreateDTO
from app.domain.users.models import User
from app.domain.booking.models import Order, OrderStatus, TicketInstance, Ticket
from app.services.invoices_service import issue_invoice_for_order
from app.core.auditing import AuditSpan
import uuid
import hashlib
from app.domain.exceptions import NotFound, Conflict, InvalidInput


def _redirect_url(payment: Payment, idempotency_key: str) -> str:
    return f"/payments/{payment.id}/redirect?ik={idempotency_key}"


def _normalize_uuid4(key: str) -> str:
    if not key or not key.strip():
        raise InvalidInput("Idempotency key is required")
    try:
        u = uuid.UUID(key.strip(), version=4)
    except ValueError as e:
        raise InvalidInput("Idempotency key must be UUIDv4") from e
    return str(u)


def _ik_digest(idempotency_key: str) -> str:
    return hashlib.sha256(idempotency_key.encode()).hexdigest()[:16]


async def _issue_tickets(db: AsyncSession, order: Order) -> int:
    ticket_instances = await db.scalars(
        select(TicketInstance)
        .where(TicketInstance.order_id == order.id)
        .outerjoin(Ticket)
        .where(Ticket.id.is_(None))
    )
    cnt = 0
    for ticket_instance in ticket_instances.all():
        db.add(Ticket(ticket_instance_id=ticket_instance.id))
        cnt += 1
    await db.flush()
    return cnt


async def _require_payment_method(db: AsyncSession, pm_id: int) -> PaymentMethod:
    pm = await crud.get_payment_method(db, pm_id)
    if not pm:
        raise NotFound("Payment method not found", ctx={"payment_method_id": pm_id})
    return pm


async def _require_active_payment_method(db: AsyncSession, pm_id: int) -> PaymentMethod:
    pm = await _require_payment_method(db, pm_id)
    if not pm.is_active:
        raise NotFound("Payment method not found", ctx={"payment_method_id": pm_id, "inactive": True})
    return pm


async def _require_awaiting_order(db: AsyncSession, user_id: int) -> Order:
    order = await db.scalar(
        select(Order)
        .where(Order.user_id == user_id, Order.status == OrderStatus.AWAITING_PAYMENT)
        .with_for_update()
    )
    if not order:
        raise NotFound("No order awaiting payment", ctx={"user_id": user_id})

    now = datetime.now(timezone.utc)
    if order.reserved_until < now:
        raise Conflict(
            "Reservation expired",
            ctx={"order_id": order.id, "reserved_until": order.reserved_until.isoformat()}
        )
    if order.total_price is None or order.total_price <= 0:
        raise InvalidInput(
            "Order total must be greater than zero",
            ctx={"order_id": order.id, "total_price": str(order.total_price)}
        )

    return order


async def _require_payment_for_user(db: AsyncSession, payment_id: int, user_id: int, *, for_update: bool = False) -> Payment:
    stmt = (
        select(Payment)
        .join(Order)
        .where(Payment.id == payment_id, Order.user_id == user_id)
    )
    if for_update:
        stmt = stmt.with_for_update()
    payment = await db.scalar(stmt)
    if not payment:
        raise NotFound("Payment not found", ctx={"payment_id": payment_id, "user_id": user_id})
    return payment


async def get_payment_method(db: AsyncSession, payment_method_id: int) -> PaymentMethod:
    return await _require_payment_method(db, payment_method_id)


async def list_all_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    return await crud.list_payment_methods(db)


async def list_active_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    return await crud.list_active_payment_methods(db)


async def create_payment_method(db: AsyncSession, schema: PaymentMethodCreateDTO) -> PaymentMethod:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        scope="PAYMENT_METHODS",
        action="CREATE",
        object_type="payment_method",
        meta={"fields": fields}
    ) as span:
        payment_method = await crud.create_payment_method(db, schema.model_dump(exclude_none=True))
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("Payment method already exists", ctx={"fields": fields}) from e
        span.object_id = payment_method.id
        return payment_method


async def update_payment_method(
        db: AsyncSession,
        payment_method_id: int,
        schema: PaymentMethodUpdateDTO,
) -> PaymentMethod:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        scope="PAYMENT_METHODS",
        action="UPDATE",
        object_type="payment_method",
        object_id=payment_method_id,
        meta={"fields": fields}
    ):
        payment_method = await get_payment_method(db, payment_method_id)
        payment_method = await crud.update_payment_method(payment_method, schema.model_dump(exclude_none=True))
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("Payment method already exists", ctx={"fields": fields}) from e
        return payment_method


async def start_payment(
        db: AsyncSession,
        user: User,
        schema: PaymentCreateDTO,
        idempotency_key: str
) -> tuple[Payment, str | None]:
    idempotency_key = _normalize_uuid4(idempotency_key)
    ik_d = _ik_digest(idempotency_key)

    async with AuditSpan(
        scope="PAYMENTS",
        action="START",
        object_type="payment",
        meta={"payment_method_id": schema.payment_method_id, "ik_digest": ik_d},
    ) as span:
        order = await _require_awaiting_order(db, user.id)
        payment_method = await _require_active_payment_method(db, schema.payment_method_id)
        amount = order.total_price
        span.meta.update({"order_id": order.id, "amount": str(amount)})

        existing_by_key = await db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
        if existing_by_key:
            if (existing_by_key.order_id != order.id or
                    existing_by_key.payment_method_id != payment_method.id or
                    existing_by_key.amount != amount):
                raise Conflict(
                    "Idempotency key reused for different payload",
                    ctx={
                        "payment_id": existing_by_key.id,
                        "order_id": order.id,
                        "payment_method_id": payment_method.id,
                        "amount": str(amount)
                    }
                )

            span.object_id = existing_by_key.id
            redirect_url = (
                _redirect_url(existing_by_key, idempotency_key) if existing_by_key.status in (
                    PaymentStatus.PENDING, PaymentStatus.REQUIRES_ACTION
                ) else None
            )
            span.meta.update({"status": existing_by_key.status, "redirect": bool(redirect_url), "idempotent_hit": True})
            return existing_by_key, redirect_url

        existing_active = await db.scalar(
            select(Payment)
            .where(
                Payment.order_id == order.id,
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.REQUIRES_ACTION])
            )
        )

        if existing_active:
            if existing_active.payment_method_id == payment_method.id and existing_active.amount == amount:
                if existing_active.status in (PaymentStatus.PENDING, PaymentStatus.REQUIRES_ACTION):
                    span.object_id = existing_active.id
                    span.meta.update({"status": existing_active.status, "redirect": True, "reused_active": True})
                    return existing_active, _redirect_url(existing_active, existing_active.idempotency_key)
                span.object_id = existing_active.id
                span.meta.update({"status": existing_active.status, "redirect": False, "reused_active": True})
                return existing_active, None
            raise Conflict(
                "Active payment already exists for this order",
                ctx={"order_id": order.id, "payment_id": existing_active.id, "status": existing_active.status},
            )

        payment = Payment(
            order_id=order.id,
            payment_method_id=payment_method.id,
            amount=amount,
            provider="test",
            status=PaymentStatus.REQUIRES_ACTION,
            idempotency_key=idempotency_key
        )
        db.add(payment)
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict(
                "Payment already exists for this order",
                ctx={"order_id": order.id, "ik_digest": ik_d}
            ) from e

        span.object_id = payment.id
        span.meta.update({"status": payment.status, "redirect": True})
        redirect_url = _redirect_url(payment, idempotency_key)
        return payment, redirect_url


async def finalize_payment(
        db: AsyncSession,
        user: User,
        payment_id: int,
        success: bool,
) -> Payment:
    async with AuditSpan(scope="PAYMENTS", action="FINALIZE", object_type="payment", meta={"success": success}) as span:
        payment = await _require_payment_for_user(db, payment_id, user.id, for_update=True)
        span.object_id = payment.id
        span.order_id = payment.order_id
        span.meta.update({"prev_status": payment.status})

        order = payment.order
        if not order or order.status != OrderStatus.AWAITING_PAYMENT:
            raise Conflict("Order not awaiting payment", ctx={"order_id": getattr(order, "id", None)})

        if payment.status == PaymentStatus.COMPLETED or payment.status == PaymentStatus.FAILED:
            span.meta.update({"new_status": payment.status, "no_op": True})
            return payment

        now = datetime.now(timezone.utc)
        if success:
            payment.status = PaymentStatus.COMPLETED
            payment.paid_at = now
            order.status = OrderStatus.COMPLETED

            invoice_issued = False
            if order.invoice_requested and order.invoice:
                inv = await issue_invoice_for_order(db, order, now)
                invoice_issued = bool(inv and inv.issued_at)

            tickets_added = await _issue_tickets(db, order)
            await db.flush()
            span.meta.update({
                "new_status": payment.status,
                "invoice_issued": invoice_issued,
                "tickets_added": tickets_added
            })
            return payment

        payment.status = PaymentStatus.FAILED
        await db.flush()
        span.meta.update({"new_status": payment.status})
        return payment


async def get_payment_for_user(db: AsyncSession, payment_id: int, user: User) -> Payment:
    return await _require_payment_for_user(db, payment_id, user.id, for_update=False)
