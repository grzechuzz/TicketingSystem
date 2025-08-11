from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import insert
from app.domain.booking.models import Order, OrderStatus, TicketInstance
from app.domain.events.models import Event, EventStatus
from app.domain.event_catalog.models import EventTicketType, EventSector
from app.domain.venues.models import Seat
from app.domain.users.models import User


async def reserve_ticket(
        db: AsyncSession,
        user: User,
        event_id: int,
        event_ticket_type_id: int,
        seat_id: int | None = None
) -> tuple[Order, TicketInstance]:
    """
    Reserve a ticket for user + creates order if necessary
    - Validates connections betweeen event -> ticket type -> seat
    - Checks ticket limits for specific user
    - Prevents overselling & order correctness by utilizing FOR UPDATE clause and UNIQUE constraints
    ALL in ONE transaction (important!)
    """
    async with db.begin():
        # Part 1 - check whether event_id is correct and sale is active
        event = await db.scalar(select(Event).where(
            Event.id == event_id,
            Event.status == EventStatus.ON_SALE))
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
                index_where=(Order.status == OrderStatus.PENDING)
            )
        )

        order = await db.scalar(
            select(Order)
            .where(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
            .with_for_update()
        )

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
                    order_id=order.id
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
                order_id=order.id
            )
            db.add(ticket_instance)
            await db.flush()

        # Part 6 - ticket prices & vat rate snapshots
        price = event_ticket_type.price_net * event_ticket_type.vat_rate
        price_gross = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        order.total_price = (order.total_price or Decimal("0")) + price_gross
        order.reserved_until = now + timedelta(minutes=20)

    return order, ticket_instance
