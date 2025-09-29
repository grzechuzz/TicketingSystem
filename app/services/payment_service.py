from datetime import datetime, timezone
from fastapi import HTTPException, status, Request
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


def _redirect_url(payment: Payment, idempotency_key: str) -> str:
    return f"/payments/{payment.id}/redirect?ik={idempotency_key}"


def _normalize_uuid4(key: str) -> str:
    if not key or not key.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency key is required")
    try:
        u = uuid.UUID(key.strip(), version=4)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency key must be UUIDv4")
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


async def get_payment_method(db: AsyncSession, payment_method_id: int) -> PaymentMethod:
    payment_method = await crud.get_payment_method(db, payment_method_id)
    if not payment_method:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    return payment_method


async def list_all_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    return await crud.list_payment_methods(db)


async def list_active_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    return await crud.list_active_payment_methods(db)


async def create_payment_method(db: AsyncSession, schema: PaymentMethodCreateDTO, user: User, request: Request) -> PaymentMethod:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="PAYMENT_METHODS",
        action="CREATE",
        user=user,
        object_type="payment_method",
        meta={"fields": fields}
    ) as span:
        payment_method = await crud.create_payment_method(db, schema.model_dump(exclude_none=True))
        try:
            await db.flush()
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment method already exists")
        span.object_id = payment_method.id
        return payment_method


async def update_payment_method(
        db: AsyncSession,
        payment_method_id: int,
        schema: PaymentMethodUpdateDTO,
        user: User,
        request: Request
) -> PaymentMethod:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="PAYMENT_METHODS",
        action="UPDATE",
        user=user,
        object_type="payment_method",
        object_id=payment_method_id,
        meta={"fields": fields}
    ):
        payment_method = await get_payment_method(db, payment_method_id)
        payment_method = await crud.update_payment_method(payment_method, schema.model_dump(exclude_none=True))
        try:
            await db.flush()
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment method already exists")
        return payment_method


async def start_payment(
        db: AsyncSession,
        user: User,
        schema: PaymentCreateDTO,
        idempotency_key: str,
        request: Request
) -> tuple[Payment, str | None]:
    idempotency_key = _normalize_uuid4(idempotency_key)

    async with AuditSpan(
        request,
        scope="PAYMENTS",
        action="START",
        user=user,
        object_type="payment",
        meta={"payment_method_id": schema.payment_method_id, "ik_digest": _ik_digest(idempotency_key)},
    ) as span:
        order = await db.scalar(
            select(Order)
            .where(Order.user_id == user.id, Order.status == OrderStatus.AWAITING_PAYMENT)
            .with_for_update()
        )
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No order awaiting payment")

        now = datetime.now(timezone.utc)
        if order.reserved_until < now:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation expired")

        if order.total_price is None or order.total_price <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order total must be greater than zero")

        payment_method = await get_payment_method(db, schema.payment_method_id)
        if not payment_method or not payment_method.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")

        amount = order.total_price
        span.meta.update({"order_id": order.id, "amount": str(amount)})

        existing_by_key = await db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
        if existing_by_key:
            if (existing_by_key.order_id != order.id or
                    existing_by_key.payment_method_id != payment_method.id or
                    existing_by_key.amount != amount):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key reused for different payload"
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active payment already exists for this order"
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
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already exists for this order")

        span.object_id = payment.id
        span.meta.update({"status": payment.status, "redirect": True})
        redirect_url = _redirect_url(payment, idempotency_key)
        return payment, redirect_url


async def finalize_payment(
        db: AsyncSession,
        user: User,
        payment_id: int,
        success: bool,
        request: Request
) -> Payment:
    async with AuditSpan(
        request,
        scope="PAYMENTS",
        action="FINALIZE",
        user=user,
        object_type="payment",
        meta={"success": success}
    ) as span:
        payment = await db.scalar(
            select(Payment)
            .join(Order)
            .where(
                Payment.id == payment_id,
                Order.user_id == user.id
            )
            .with_for_update()
        )
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        span.object_id = payment.id
        span.order_id = payment.order_id
        span.meta.update({"prev_status": payment.status})

        order = payment.order
        if not order or order.status != OrderStatus.AWAITING_PAYMENT:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order not awaiting payment")

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
    payment = await db.scalar(
        select(Payment)
        .join(Order)
        .where(Payment.id == payment_id, Order.user_id == user.id)
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment
