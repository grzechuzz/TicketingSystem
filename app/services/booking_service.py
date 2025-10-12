from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.dialects.postgresql import insert
from app.domain.booking.models import Order, OrderStatus, TicketInstance, TicketHolder, Invoice
from app.domain.events.models import Event, EventStatus
from app.domain.pricing.models import EventTicketType
from app.domain.allocation.models import EventSector
from app.domain.payments.models import Payment, PaymentStatus
from app.domain.venues.models import Seat, Sector
from app.domain.users.models import User
from app.domain.booking.schemas import TicketHolderUpsertDTO, InvoiceRequestDTO, InvoiceUpsertDTO
from app.core.auditing import AuditSpan
from app.domain.exceptions import NotFound, Conflict, Unprocessable, InvalidInput

RESERVATION_MINUTES = 15
CENT = Decimal("0.01")


def _extend_reservation(order: Order, now: datetime, minutes: int = RESERVATION_MINUTES) -> None:
    target = now + timedelta(minutes=minutes)
    order.reserved_until = max(order.reserved_until, target) if order.reserved_until else target


def _bump_total(order: Order, delta: Decimal) -> None:
    current_price = order.total_price or Decimal("0")
    new_price = current_price + delta
    order.total_price = new_price if new_price > 0 else Decimal("0")


def _gross_price(price_net: Decimal, vat_rate: Decimal) -> Decimal:
    return (price_net * vat_rate).quantize(CENT, rounding=ROUND_HALF_UP)


async def _require_event_on_sale_status(db: AsyncSession, event_id: int) -> Event:
    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.status == EventStatus.ON_SALE)
    )
    if not event:
        raise NotFound("Event not found or sale not started", ctx={"event_id": event_id})

    now = datetime.now(timezone.utc)
    if event.sales_start > now:
        raise Conflict("Sales not started yet", ctx={"event_id": event_id})
    if event.sales_end < now:
        raise Conflict("Sales ended", ctx={"event_id": event_id})
    return event


async def _load_ett_for_event(db: AsyncSession, ett_id: int, event_id: int) -> EventTicketType:
    event_ticket_type = await db.scalar(
        select(EventTicketType)
        .join(EventSector)
        .where(EventTicketType.id == ett_id, EventSector.event_id == event_id)
    )
    if not event_ticket_type:
        raise Unprocessable(
            "Ticket type does not match event",
            ctx={"event_id": event_id, "event_ticket_type_id": ett_id}
        )
    return event_ticket_type


async def _require_order(
        db: AsyncSession,
        user_id: int,
        status_: OrderStatus,
        for_update: bool = True,
        not_found_msg: str = "No pending order found"
) -> Order:
    stmt = select(Order).where(Order.user_id == user_id, Order.status == status_)
    if for_update:
        stmt = stmt.with_for_update()
    order = await db.scalar(stmt)
    if not order:
        raise NotFound(not_found_msg, ctx={"user_id": user_id, "order_status": status_.name})
    return order


async def _require_seat_in_sector(db: AsyncSession, seat_id: int, sector_id: int) -> Seat:
    seat = await db.scalar(select(Seat).where(Seat.id == seat_id))
    if not seat:
        raise NotFound("Seat not found", ctx={"seat_id": seat_id})
    if seat.sector_id != sector_id:
        raise InvalidInput(
            "Seat does not match ticket type",
            ctx={"seat_id": seat_id, "expected_sector_id": sector_id, "actual_sector_id": seat.sector_id},
        )
    return seat


async def _ensure_user_ticket_limit_not_exceeded(db: AsyncSession, user_id: int, event: Event) -> None:
    if event.max_tickets_per_user is not None:
        current_count = await db.scalar(
            select(func.count(TicketInstance.id))
            .select_from(TicketInstance)
            .join(Order)
            .where(
                Order.user_id == user_id,
                TicketInstance.event_id == event.id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT, OrderStatus.COMPLETED])
            )
        )
        if (current_count or 0) + 1 > event.max_tickets_per_user:
            raise InvalidInput("Ticket limit for this event exceeded", ctx={"user_id": user_id, "event_id": event.id})


async def _require_cart_has_items(db: AsyncSession, order_id: int) -> None:
    has_items = await db.scalar(
        select(select(1).select_from(TicketInstance).where(TicketInstance.order_id == order_id).exists())
    )
    if not has_items:
        raise InvalidInput("Cart is empty", ctx={"order_id": order_id})


async def _require_no_missing_holders(db: AsyncSession, order_id: int) -> None:
    missing_required_holder = await db.scalar(
        select(
            select(1)
            .select_from(TicketInstance)
            .join(TicketInstance.event)
            .outerjoin(TicketInstance.ticket_holder)
            .where(
                TicketInstance.order_id == order_id,
                Event.holder_data_required.is_(True),
                TicketHolder.id.is_(None),
            )
            .exists()
        )
    )
    if missing_required_holder:
        raise InvalidInput("Missing holder data", ctx={"order_id": order_id})


def _require_not_expired(order: Order, now: datetime) -> None:
    if order.reserved_until < now:
        raise Conflict(
            "Reservation expired",
            ctx={"order_id": order.id, "reserved_until": order.reserved_until.isoformat()}
        )


async def _ga_decrement(db: AsyncSession, event_sector_id: int) -> None:
    left = await db.scalar(
        update(EventSector)
        .where(EventSector.id == event_sector_id, EventSector.tickets_left > 0)
        .values(tickets_left=EventSector.tickets_left - 1)
        .returning(EventSector.tickets_left)
    )
    if left is None:
        raise Conflict("No tickets left", ctx={"event_sector_id": event_sector_id})


async def _ga_increment(db: AsyncSession, event_sector_id: int, count: int):
    await db.execute(
        update(EventSector)
        .where(EventSector.id == event_sector_id)
        .values(tickets_left=EventSector.tickets_left + int(count))
    )


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
    async with AuditSpan(
        scope='BOOKING',
        action='RESERVE_TICKET',
        object_type='ticket_instance',
        event_id=event_id,
        meta={"event_ticket_type_id": event_ticket_type_id, "seat_id": seat_id}
    ) as span:
        # Part 1 - check event status and pre-check orders in AWAITING PAYMENT status
        event = await _require_event_on_sale_status(db, event_id)
        now = datetime.now(timezone.utc)
        awaiting_order = await db.scalar(
            select(Order)
            .where(Order.user_id == user.id, Order.status == OrderStatus.AWAITING_PAYMENT)
            .with_for_update()
        )
        if awaiting_order and awaiting_order.reserved_until >= now:
            raise Conflict("Order awaiting payment", ctx={"order_id": awaiting_order.id})

        # Part 2 - verify that ticket_type is matched to the correct event
        event_ticket_type = await _load_ett_for_event(db, event_ticket_type_id, event_id)
        is_ga = event_ticket_type.event_sector.sector.is_ga
        if is_ga and seat_id is not None:
            raise InvalidInput("GA sector shouldn't include seat", ctx={"event_id": event_id})
        if not is_ga and seat_id is None:
            raise InvalidInput(
                "Seat is required for this sector",
                ctx={"event_id": event_id, "event_ticket_type_id": event_ticket_type_id}
            )

        # Part 3 - create or find existing active order
        await db.execute(
            insert(Order)
            .values(user_id=user.id)
            .on_conflict_do_nothing(
                index_elements=[Order.user_id],
                index_where=Order.status.in_([OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT])
            )
        )
        order = await _require_order(
            db,
            user.id,
            OrderStatus.PENDING,
            for_update=True
        )

        # Part 4 - check ticket limits per user for specific event
        await _ensure_user_ticket_limit_not_exceeded(db, user.id, event)

        price_net = event_ticket_type.price_net
        vat_rate = event_ticket_type.vat_rate
        price_gross = _gross_price(price_net, vat_rate)
        ticket_type_name = event_ticket_type.ticket_type.name

        # Part 5 - add ticket instance, check ticket availability and verify seat (if ticket is seated)
        if is_ga:
            await _ga_decrement(db, event_ticket_type.event_sector_id)
            ticket_instance = TicketInstance(
                event_ticket_type_id=event_ticket_type_id,
                event_id=event_id,
                order_id=order.id,
                price_net_snapshot=price_net,
                vat_rate_snapshot=vat_rate,
                price_gross_snapshot=price_gross,
                ticket_type_name_snapshot=ticket_type_name
            )
            db.add(ticket_instance)
            await db.flush()
        else:
            await _require_seat_in_sector(db, seat_id, event_ticket_type.event_sector.sector_id)
            ticket_instance = TicketInstance(
                event_ticket_type_id=event_ticket_type_id,
                seat_id=seat_id,
                event_id=event_id,
                order_id=order.id,
                price_net_snapshot=price_net,
                vat_rate_snapshot=vat_rate,
                price_gross_snapshot=price_gross,
                ticket_type_name_snapshot=ticket_type_name
            )
            db.add(ticket_instance)
            try:
                await db.flush()
            except IntegrityError:
                raise Conflict(
                    "Selected seat is not available",
                    ctx={"event_id": event_id, "event_ticket_type_id": event_ticket_type_id, "seat_id": seat_id}
                )

        # Part 6 - update order
        _bump_total(order, ticket_instance.price_gross_snapshot)
        _extend_reservation(order, now)

        span.order_id = order.id
        span.object_id = ticket_instance.id
        span.meta["is_ga"] = is_ga
        return order, ticket_instance


async def get_user_pending_order(db: AsyncSession, user: User) -> Order:
    return await _require_order(db, user.id, OrderStatus.PENDING, for_update=False)


async def remove_ticket_instance(db: AsyncSession, user: User, ticket_instance_id: int) -> None:
    async with AuditSpan(
            scope="CART",
            action="REMOVE_ITEM",
            object_type="ticket_instance",
            meta={"ticket_instance_id": ticket_instance_id}
    ) as span:
        ticket_instance = await db.scalar(select(TicketInstance).where(TicketInstance.id == ticket_instance_id))
        if not ticket_instance:
            raise NotFound("Ticket instance not found", ctx={"ticket_instance_id": ticket_instance_id})

        order = await _require_order(
            db, user.id, OrderStatus.PENDING, for_update=True, not_found_msg="Item not found in order"
        )

        if order.id != ticket_instance.order_id:
            raise NotFound(
                "Item not found in order",
                ctx={"ticket_instance_id": ticket_instance_id, "order_id": order.id}
            )

        event_ticket_type = await db.scalar(
            select(EventTicketType)
            .join(EventSector)
            .where(EventTicketType.id == ticket_instance.event_ticket_type_id)
        )
        if event_ticket_type.event_sector.sector.is_ga:
            await _ga_increment(db, event_ticket_type.event_sector_id, 1)

        _bump_total(order, -ticket_instance.price_gross_snapshot)

        await db.delete(ticket_instance)
        await db.flush()

        span.order_id = order.id
        span.event_id = ticket_instance.event_id
        span.object_id = ticket_instance_id


async def upsert_ticket_holder(
        db: AsyncSession,
        ticket_instance_id: int,
        schema: TicketHolderUpsertDTO,
        user: User,
) -> TicketHolder:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        scope="CART",
        action="UPSERT_HOLDER",
        object_type="ticket_holder",
        meta={"ticket_instance_id": ticket_instance_id, "fields": fields}
    ) as span:
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
            raise NotFound(
                "Ticket instance not found in your order",
                ctx={"ticket_instance_id": ticket_instance_id, "user_id": user.id},
            )

        requires_holder = await db.scalar(
            select(Event.holder_data_required).where(Event.id == ticket_instance.event_id)
        )
        if not requires_holder:
            raise InvalidInput("Holder data not required for this event", ctx={"event_id": ticket_instance.event_id})

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
        span.object_id = th.id
        span.order_id = ticket_instance.order_id
        span.event_id = ticket_instance.event_id
        return th


async def set_invoice_requested(db: AsyncSession, schema: InvoiceRequestDTO, user: User) -> None:
    async with AuditSpan(
            scope="CART",
            action="SET_INVOICE_REQUESTED",
            object_type="order",
            meta={"invoice_requested": schema.invoice_requested}
    ) as span:
        order = await _require_order(db, user.id, OrderStatus.PENDING, for_update=True)
        order.invoice_requested = schema.invoice_requested
        await db.flush()
        span.object_id = order.id
        span.order_id = order.id


async def upsert_invoice(db: AsyncSession, schema: InvoiceUpsertDTO, user: User) -> Invoice:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
            scope="CART",
            action="UPSERT_INVOICE",
            object_type="invoice",
            meta={"fields": fields}
    ) as span:
        order = await _require_order(db, user.id, OrderStatus.PENDING, for_update=True)
        if not order.invoice_requested:
            raise InvalidInput("Invoice not requested for this order", ctx={"order_id": order.id})

        if order.invoice:
            invoice = order.invoice
            for key, value in schema.model_dump(exclude_none=True).items():
                setattr(invoice, key, value)
        else:
            invoice = Invoice(order_id=order.id, **schema.model_dump(exclude_none=True))
            db.add(invoice)

        await db.flush()
        span.order_id = order.id
        span.object_id = invoice.id
        return invoice


async def process_order(db: AsyncSession, user: User) -> Order:
    order = await _require_order(db, user.id, OrderStatus.PENDING, for_update=True)

    now = datetime.now(timezone.utc)
    _require_not_expired(order, now)

    await _require_cart_has_items(db, order.id)

    if order.invoice_requested and not order.invoice:
        raise InvalidInput("Invoice data required", ctx={"order_id": order.id})

    await _require_no_missing_holders(db, order.id)

    order.status = OrderStatus.AWAITING_PAYMENT
    _extend_reservation(order, now)

    await db.flush()
    return order


async def checkout(db: AsyncSession, user: User) -> Order:
    async with AuditSpan(
            scope="CART",
            action="CHECKOUT",
            object_type="order"
    ) as span:
        now = datetime.now(timezone.utc)
        order = await db.scalar(
            select(Order)
            .where(Order.user_id == user.id, Order.status == OrderStatus.AWAITING_PAYMENT)
            .with_for_update()
        )
        if order:
            _require_not_expired(order, now)
            span.object_id = order.id
            span.order_id = order.id
            return order

        order = await process_order(db, user)
        span.object_id = order.id
        span.order_id = order.id
        return order


async def reopen_cart(db: AsyncSession, user: User) -> Order:
    async with AuditSpan(
            scope="CART",
            action="REOPEN",
            object_type="order"
    ) as span:
        order = await _require_order(
            db,
            user.id,
            OrderStatus.AWAITING_PAYMENT,
            for_update=True,
            not_found_msg="No order awaiting payment"
        )
        now = datetime.now(timezone.utc)
        _require_not_expired(order, now)

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
            raise Conflict("Payment in progress", ctx={"order_id": order.id})

        order.status = OrderStatus.PENDING
        _extend_reservation(order, now)

        await db.flush()
        span.object_id = order.id
        span.order_id = order.id
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
