from decimal import Decimal
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.core.pagination import PageDTO
from app.domain.users.models import User
from app.domain.booking.models import Order, TicketInstance, Ticket, TicketStatus, TicketHolder
from app.domain.venues.models import Venue
from app.domain.allocation.models import EventSector
from app.domain.pricing.models import EventTicketType
from app.domain.events.models import Event
from app.domain.venues.models import Sector, Seat
from app.domain.payments.models import Payment, PaymentStatus
from app.domain.booking.schemas import UserOrdersQueryDTO, OrderListItemDTO, OrderDetailsDTO, TicketReadItemDTO, \
    AdminOrdersQueryDTO, AdminOrderListItemDTO, AdminOrderDetailsDTO, TicketHolderPublicDTO
from app.domain.payments.schemas import PaymentInOrderDTO, PaymentMethodReadDTO


def _calc_totals_from_tickets(tickets: list[TicketInstance]) -> tuple[Decimal, Decimal, Decimal]:
    net = sum((ti.price_net_snapshot for ti in tickets), Decimal('0.00'))
    gross = sum((ti.price_gross_snapshot for ti in tickets), Decimal('0.00'))
    vat = gross - net
    return net, vat, gross


def _to_order_list_item(order: Order, items_count: int | None) -> OrderListItemDTO:
    return OrderListItemDTO(
        id=order.id,
        status=order.status,
        total_price=order.total_price,
        reserved_until=order.reserved_until,
        created_at=order.created_at,
        items_count=items_count
    )


def _to_payment_in_order(payment: Payment) -> PaymentInOrderDTO:
    payment_method = payment.payment_method
    return PaymentInOrderDTO(
        id=payment.id,
        amount=payment.amount,
        payment_method=PaymentMethodReadDTO(
            id=payment_method.id,
            name=payment_method.name,
            is_active=payment_method.is_active
        ),
        paid_at=payment.paid_at,
        provider=payment.provider
    )


def _to_order_details(order: Order, payment_dto: PaymentInOrderDTO | None) -> OrderDetailsDTO:
    return OrderDetailsDTO(
        id=order.id,
        status=order.status,
        total_price=order.total_price,
        reserved_until=order.reserved_until,
        created_at=order.created_at,
        items=list(order.ticket_instances),
        payment=payment_dto
    )


async def list_user_orders(
        db: AsyncSession,
        user: User,
        query: UserOrdersQueryDTO,
) -> PageDTO[OrderListItemDTO]:
    where = [Order.user_id == user.id]
    if query.status is not None:
        where.append(Order.status == query.status)

    total = await db.scalar(select(func.count()).select_from(Order).where(*where))

    ti_count = (
        select(func.count(TicketInstance.id))
        .where(TicketInstance.order_id == Order.id)
        .correlate(Order)
        .scalar_subquery()
    )

    rows = await db.execute(
        select(Order, ti_count.label("items_count"))
        .where(*where)
        .order_by(desc(Order.created_at), Order.id)
        .limit(query.page_size)
        .offset((query.page - 1) * query.page_size)
    )

    items = []
    for order, items_count in rows.all():
        items.append(_to_order_list_item(order, int(items_count or 0)))

    return PageDTO[OrderListItemDTO](items=items, total=int(total or 0), page=query.page, page_size=query.page_size)


async def get_user_order(db: AsyncSession, user: User, order_id: int) -> OrderDetailsDTO:
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    payment = await db.scalar(
        select(Payment)
        .where(Payment.order_id == order_id, Payment.status == PaymentStatus.COMPLETED)
    )
    payment_dto = _to_payment_in_order(payment) if payment else None

    return _to_order_details(order, payment_dto)


async def list_user_active_tickets(db: AsyncSession, user: User) -> list[TicketReadItemDTO]:
    rows = await db.execute(
        select(
            Ticket.id,
            Ticket.code,
            Ticket.status,
            Ticket.created_at,
            Event.id.label('event_id'),
            Event.name.label('event_name'),
            Event.event_start,
            Venue.name.label("venue_name"),
            Sector.is_ga,
            Sector.name.label('sector_name'),
            Seat.row,
            Seat.number.label("seat"),
            TicketInstance.ticket_type_name_snapshot.label("ticket_type_name"),
            TicketInstance.price_gross_snapshot.label("price_gross"),
            TicketHolder.id.label('holder_id'),
            TicketHolder.first_name,
            TicketHolder.last_name,
            TicketHolder.identification_number
        )
        .select_from(Ticket)
        .join(TicketInstance)
        .join(Order)
        .join(Event)
        .join(Venue, Venue.id == Event.venue_id)
        .join(EventTicketType)
        .join(EventSector)
        .join(Sector)
        .outerjoin(Seat, Seat.id == TicketInstance.seat_id)
        .outerjoin(TicketHolder, TicketHolder.ticket_instance_id == TicketInstance.id)
        .where(Order.user_id == user.id, Ticket.status == TicketStatus.ACTIVE)
        .order_by(desc(Ticket.created_at), Ticket.id)
    )

    items = []
    for r in rows.all():
        holder = None
        if r.holder_id is not None:
            suffix = (r.identification_number or "")[-4:]
            holder = TicketHolderPublicDTO(
                id=r.holder_id,
                first_name=r.first_name,
                last_name=r.last_name,
                identification_suffix=suffix
            )
        items.append(
            TicketReadItemDTO(
                id=r.id,
                code=r.code,
                status=r.status,
                created_at=r.created_at,
                event_id=r.event_id,
                event_name=r.event_name,
                event_start=r.event_start,
                venue_name=r.venue_name,
                is_ga=r.is_ga,
                sector_name=r.sector_name,
                row=r.row,
                seat=r.seat,
                ticket_type_name=r.ticket_type_name,
                price_gross=r.price_gross,
                holder=holder
            )
        )

    return items


async def list_orders_admin(db: AsyncSession, query: AdminOrdersQueryDTO) -> PageDTO[AdminOrderListItemDTO]:
    where = []
    if query.status is not None:
        where.append(Order.status == query.status)
    if query.created_from:
        where.append(Order.created_at >= query.created_from)
    if query.created_to:
        where.append(Order.created_at <= query.created_to)
    if query.user_id is not None:
        where.append(Order.user_id == query.user_id)
    if query.email is not None:
        where.append(Order.user.has(func.lower(User.email) == func.lower(query.email)))

    total = await db.scalar(select(func.count()).select_from(Order).where(*where))

    ti_count = (
        select(func.count(TicketInstance.id))
        .where(TicketInstance.order_id == Order.id)
        .correlate(Order)
        .scalar_subquery()
    )

    rows = await db.execute(
        select(
            Order,
            ti_count.label("items_count"),
            User.id.label("user_id"),
            User.email.label("user_email")
        )
        .join(User)
        .where(*where)
        .order_by(desc(Order.created_at), Order.id)
        .limit(query.page_size)
        .offset((query.page - 1) * query.page_size)
    )

    items = []
    for order, items_count, user_id, user_email in rows.all():
        items.append(
            AdminOrderListItemDTO(
                id=order.id,
                status=order.status,
                total_price=order.total_price,
                reserved_until=order.reserved_until,
                created_at=order.created_at,
                items_count=int(items_count or 0),
                user_id=user_id,
                user_email=user_email
            )
        )

    return PageDTO[AdminOrderListItemDTO](
        items=items,
        total=int(total or 0),
        page=query.page,
        page_size=query.page_size
    )


async def get_order_admin(db: AsyncSession, order_id: int) -> AdminOrderDetailsDTO:
    row = await db.execute(
        select(Order, User.email.label("user_email"))
        .join(User)
        .where(Order.id == order_id)
    )
    result = row.first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order, user_email = result

    payment = await db.scalar(
        select(Payment)
        .where(Payment.order_id == order.id, Payment.status == PaymentStatus.COMPLETED)
    )
    payment_dto = _to_payment_in_order(payment) if payment else None

    return AdminOrderDetailsDTO(
        id=order.id,
        status=order.status,
        total_price=order.total_price,
        reserved_until=order.reserved_until,
        created_at=order.created_at,
        items=list(order.ticket_instances),
        payment=payment_dto,
        user_id=order.user_id,
        user_email=user_email
    )
