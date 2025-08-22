from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.payments import crud
from app.domain.payments.models import PaymentMethod, Payment, PaymentStatus
from app.domain.payments.schemas import PaymentMethodCreateDTO, PaymentMethodUpdateDTO, PaymentCreateDTO
from app.domain.users.models import User
from app.domain.booking.models import Order, OrderStatus, TicketInstance, Ticket
import uuid


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


async def _generate_ticket_code() -> str:
    return uuid.uuid4().hex


async def _issue_tickets(db: AsyncSession, order: Order) -> None:
    ticket_instances = await db.scalars(
        select(TicketInstance)
        .where(TicketInstance.order_id == order.id)
        .outerjoin(Ticket)
        .where(Ticket.id.is_(None))
    )
    for ticket_instance in ticket_instances.all():
        code = await _generate_ticket_code()
        db.add(Ticket(ticket_instance_id=ticket_instance.id, code=code))
    await db.flush()


async def get_payment_method(db: AsyncSession, payment_method_id: int) -> PaymentMethod:
    payment_method = await crud.get_payment_method(db, payment_method_id)
    if not payment_method:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    return payment_method


async def list_all_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    return await crud.list_payment_methods(db)


async def list_active_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    return await crud.list_active_payment_methods(db)


async def create_payment_method(db: AsyncSession, schema: PaymentMethodCreateDTO) -> PaymentMethod:
    payment_method = await crud.create_payment_method(db, schema.model_dump(exclude_none=True))
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment method already exists")
    return payment_method


async def update_payment_method(db: AsyncSession, payment_method_id: int,
                                schema: PaymentMethodUpdateDTO) -> PaymentMethod:
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
        idempotency_key: str
) -> tuple[Payment, str | None]:
    idempotency_key = _normalize_uuid4(idempotency_key)

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

    existing_by_key = await db.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )
    if existing_by_key:
        if (existing_by_key.order_id != order.id or
                existing_by_key.payment_method_id != payment_method.id or
                existing_by_key.amount != amount):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key reused for different payload"
            )

        redirect_url = (
            _redirect_url(existing_by_key, idempotency_key) if existing_by_key.status in (
                PaymentStatus.PENDING, PaymentStatus.REQUIRES_ACTION
            ) else None
        )
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
                return existing_active, _redirect_url(existing_active, existing_active.idempotency_key)
            return existing_active, None
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active payment already exists for this order")

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

    redirect_url = _redirect_url(payment, idempotency_key)
    return payment, redirect_url


async def finalize_payment(
        db: AsyncSession,
        user: User,
        payment_id: int,
        success: bool
) -> Payment:
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

    order = payment.order
    if not order or order.status != OrderStatus.AWAITING_PAYMENT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order not awaiting payment")

    if payment.status == PaymentStatus.COMPLETED or payment.status == PaymentStatus.FAILED:
        return payment

    now = datetime.now(timezone.utc)

    if success:
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = now
        order.status = OrderStatus.COMPLETED
        await _issue_tickets(db, order)
        await db.flush()
        return payment

    payment.status = PaymentStatus.FAILED
    await db.flush()
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
