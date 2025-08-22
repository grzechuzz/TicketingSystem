from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.dialects.postgresql import insert
from app.domain.booking.models import Order, OrderStatus, TicketInstance, TicketHolder, Invoice
from app.domain.events.models import Event, EventStatus
from app.domain.event_catalog.models import EventTicketType, EventSector
from app.domain.payments.models import Payment, PaymentStatus
from app.domain.venues.models import Seat, Sector
from app.domain.users.models import User
from app.domain.booking.schemas import TicketHolderUpsertDTO, InvoiceRequestDTO, InvoiceUpsertDTO


async def reserve_ticket(
        db: AsyncSession,
        user: User,
        event_id: int,
        event_ticket_type_id: int,
        seat_id: int | None = None
) -> tuple[Order, TicketInstance]:
    """
    Reserve a ticket for user + creates order if necessary
    - Validates connections between event -> ticket type -> seat
    - Checks ticket limits for specific user
    - Prevents overselling & order correctness by utilizing FOR UPDATE clause and UNIQUE constraints
    """

    # Part 1 - check whether event_id is correct and sale is active
    event = await db.scalar(select(Event).where(
        Event.id == event_id, Event.status == EventStatus.ON_SALE))
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found or sale not started")

    now = datetime.now(timezone.utc)
    if event.sales_start > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sales not started yet")

    if event.sales_end < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sales ended")

    # Part 2 - verify that ticket_type is matched to the correct event
    event_ticket_type = await db.scalar(
        select(EventTicketType)
        .join(EventSector)
        .where(EventTicketType.id == event_ticket_type_id, EventSector.event_id == event_id)
    )

    if not event_ticket_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket type does not match event")

    is_ga = event_ticket_type.event_sector.sector.is_ga
    if is_ga and seat_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GA sector shouldn't include seat")
    if not is_ga and seat_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seat is required for this sector")

    # Part 3 - create or find existing active order
    await db.execute(
        insert(Order)
        .values(user_id=user.id)
        .on_conflict_do_nothing(
            index_elements=[Order.user_id],
            index_where=Order.status.in_([OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT])
        )
    )
    order = await db.scalar(
        select(Order)
        .where(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
        .with_for_update()
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found or not in PENDING status")

    # Part 4 - check ticket limits per user for specific event
    if event.max_tickets_per_user is not None:
        current_count = await db.scalar(
            select(func.count(TicketInstance.id))
            .select_from(TicketInstance)
            .join(Order)
            .where(
                Order.user_id == user.id,
                TicketInstance.event_id == event_id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT, OrderStatus.COMPLETED])
            )
        )
        if current_count + 1 > event.max_tickets_per_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticket limit for this event exceeded"
            )

    price_net = event_ticket_type.price_net
    vat_rate = event_ticket_type.vat_rate
    price_gross = (price_net * vat_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Part 5 - add ticket instance, check ticket availability and verify seat (if ticket is seated)
    if seat_id is not None:
        seat = await db.scalar(select(Seat).where(Seat.id == seat_id))
        if not seat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
        if seat.sector_id != event_ticket_type.event_sector.sector_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seat does not match ticket type")

        try:
            ticket_instance = TicketInstance(
                event_ticket_type_id=event_ticket_type_id,
                seat_id=seat_id,
                event_id=event_id,
                order_id=order.id,
                price_net_snapshot=price_net,
                vat_rate_snapshot=vat_rate,
                price_gross_snapshot=price_gross
            )
            db.add(ticket_instance)
            await db.flush()
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected seat is not available")
    else:
        left = await db.scalar(
            update(EventSector)
            .where(EventSector.id == event_ticket_type.event_sector.id, EventSector.tickets_left > 0)
            .values(tickets_left=EventSector.tickets_left - 1)
            .returning(EventSector.tickets_left)
        )
        if left is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No tickets left")

        ticket_instance = TicketInstance(
            event_ticket_type_id=event_ticket_type_id,
            event_id=event_id,
            order_id=order.id,
            price_net_snapshot=price_net,
            vat_rate_snapshot=vat_rate,
            price_gross_snapshot=price_gross
        )
        db.add(ticket_instance)
        await db.flush()

    # Part 6 - update order
    order.total_price = (order.total_price or Decimal("0")) + ticket_instance.price_gross_snapshot
    order.reserved_until = now + timedelta(minutes=20)

    return order, ticket_instance


async def get_user_pending_order(db: AsyncSession, user: User) -> Order:
    pending_order = await db.scalar(
        select(Order).where(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
    )
    if not pending_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending order found")
    return pending_order


async def remove_ticket_instance(db: AsyncSession, user: User, ticket_instance_id: int) -> None:
    ticket_instance = await db.scalar(select(TicketInstance).where(TicketInstance.id == ticket_instance_id))
    if not ticket_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket instance not found")

    order = await db.scalar(
        select(Order)
        .where(
            Order.id == ticket_instance.order_id,
            Order.user_id == user.id,
            Order.status == OrderStatus.PENDING
        )
        .with_for_update()
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in order")

    event_ticket_type = await db.scalar(
        select(EventTicketType)
        .join(EventSector)
        .join(Sector)
        .where(EventTicketType.id == ticket_instance.event_ticket_type_id)
    )

    if event_ticket_type.event_sector.sector.is_ga:
        await db.execute(
            update(EventSector)
            .where(EventSector.id == event_ticket_type.event_sector_id)
            .values(tickets_left=EventSector.tickets_left + 1)
        )

    gross = ticket_instance.price_gross_snapshot
    order.total_price = max((order.total_price or Decimal("0")) - gross, Decimal("0"))

    await db.delete(ticket_instance)
    await db.flush()


async def upsert_ticket_holder(
        db: AsyncSession,
        ticket_instance_id: int,
        schema: TicketHolderUpsertDTO,
        user: User
) -> TicketHolder:
    ticket_instance = await db.scalar(
        select(TicketInstance)
        .join(Order)
        .where(
            TicketInstance.id == ticket_instance_id,
            Order.user_id == user.id,
            Order.status == OrderStatus.PENDING
        )
        .with_for_update()
    )
    if not ticket_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket instance not found in your order")

    requires_holder = await db.scalar(
        select(Event.holder_data_required).where(Event.id == ticket_instance.event_id)
    )
    if not requires_holder:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Holder data not required for this event")

    if ticket_instance.ticket_holder:
        th = ticket_instance.ticket_holder
        th.first_name = schema.first_name
        th.last_name = schema.last_name
        th.birth_date = schema.birth_date
        th.identification_number = schema.identification_number
    else:
        th = TicketHolder(ticket_instance_id=ticket_instance.id, **schema.model_dump(exclude_none=True))
        db.add(th)

    await db.flush()
    return th


async def set_invoice_requested(db: AsyncSession, schema: InvoiceRequestDTO, user: User) -> None:
    order = await db.scalar(
        select(Order)
        .where(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
        .with_for_update()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending order found")

    order.invoice_requested = schema.invoice_requested
    await db.flush()


async def upsert_invoice(db: AsyncSession, schema: InvoiceUpsertDTO, user: User) -> Invoice:
    order = await db.scalar(
        select(Order)
        .where(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
        .with_for_update()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending order found")

    if not order.invoice_requested:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice not requested for this order")

    if order.invoice:
        invoice = order.invoice
        for key, value in schema.model_dump(exclude_none=True).items():
            setattr(invoice, key, value)
    else:
        invoice = Invoice(order_id=order.id, **schema.model_dump(exclude_none=True))
        db.add(invoice)

    await db.flush()
    return invoice


async def process_order(db: AsyncSession, user: User) -> Order:
    order = await db.scalar(
        select(Order)
        .where(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
        .with_for_update()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending order found")

    now = datetime.now(timezone.utc)

    if order.reserved_until < now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation expired")

    has_items = await db.scalar(
        select(
            select(1)
            .select_from(TicketInstance)
            .where(TicketInstance.order_id == order.id)
            .exists()
        )
    )
    if not has_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    if order.invoice_requested and not order.invoice:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice data required")

    missing_required_holder = await db.scalar(
        select(
            select(1)
            .select_from(TicketInstance)
            .join(TicketInstance.event)
            .outerjoin(TicketInstance.ticket_holder)
            .where(
                TicketInstance.order_id == order.id,
                Event.holder_data_required.is_(True),
                TicketHolder.id.is_(None)
            )
            .exists()
        )
    )
    if missing_required_holder:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing holder data")

    order.status = OrderStatus.AWAITING_PAYMENT
    order.reserved_until = max(order.reserved_until, now + timedelta(minutes=20))

    await db.flush()
    return order


async def checkout(db: AsyncSession, user: User) -> Order:
    order = await db.scalar(
        select(Order)
        .where(Order.user_id == user.id, Order.status == OrderStatus.AWAITING_PAYMENT)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)

    if order:
        if order.reserved_until < now:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reservation expired")
        return order

    return await process_order(db, user)


async def reopen_cart(db: AsyncSession, user: User) -> Order:
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

    active_payment_exists = await db.scalar(
        select(
            select(1)
            .select_from(Payment)
            .where(
                Payment.order_id == order.id,
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.REQUIRES_ACTION])
            )
            .exists()
        )
    )
    if active_payment_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment in progress")

    order.status = OrderStatus.PENDING
    order.reserved_until = max(order.reserved_until, now + timedelta(minutes=20))
    await db.flush()
    return order


async def cleanup_expired_reservations(db: AsyncSession, limit: int = 500) -> dict:
    now = datetime.now(timezone.utc)
    stats = {"orders_cancelled": 0, "tickets_released": 0, "ga_released": 0}

    pending_ids = await db.scalars(
        select(Order.id)
        .where(
            Order.status == OrderStatus.PENDING,
            Order.reserved_until < now
        )
        .with_for_update(skip_locked=True)
        .limit(limit)
    )
    pending_ids = list(pending_ids)

    active_payments_exists = (
        select(Payment.id)
        .where(
            Payment.order_id == Order.id,
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.REQUIRES_ACTION])
        )
        .exists()
    )

    awaiting_ids = await db.scalars(
        select(Order.id)
        .where(
            Order.status == OrderStatus.AWAITING_PAYMENT,
            Order.reserved_until < now,
            ~active_payments_exists
        )
        .with_for_update(skip_locked=True)
        .limit(max(0, limit - len(pending_ids)))
    )
    awaiting_ids = list(awaiting_ids)

    all_ids = pending_ids + awaiting_ids
    if not all_ids:
        return stats

    for order_id in all_ids:
        rows = await db.execute(
            select(EventSector.id, func.count(TicketInstance.id))
            .select_from(TicketInstance)
            .join(EventTicketType)
            .join(EventSector)
            .join(Sector)
            .where(TicketInstance.order_id == order_id, Sector.is_ga.is_(True))
            .group_by(EventSector.id)
        )

        for event_sector_id, cnt in rows.all():
            await db.execute(
                update(EventSector)
                .where(EventSector.id == event_sector_id)
                .values(tickets_left=EventSector.tickets_left + int(cnt))
            )
            stats["ga_released"] += int(cnt)

        delete_result = await db.execute(
            delete(TicketInstance).where(TicketInstance.order_id == order_id)
        )
        stats["tickets_released"] += int(delete_result.rowcount or 0)

        await db.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.CANCELLED)
        )
        stats["orders_cancelled"] += 1

    await db.flush()
    return stats
