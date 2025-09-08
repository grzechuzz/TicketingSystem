from decimal import Decimal
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.core.pagination import PageDTO
from app.domain.users.models import User
from app.domain.booking.models import Order, TicketInstance
from app.domain.payments.models import Payment, PaymentStatus
from app.domain.booking.schemas import UserOrdersQueryDTO, OrderListItemDTO, OrderDetailsDTO, \
    AdminOrdersQueryDTO, AdminOrderListItemDTO, AdminOrderDetailsDTO
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


def _ticket_instance_count_subquery():
    return (
        select(func.count(TicketInstance.id))
        .where(TicketInstance.order_id == Order.id)
        .correlate(Order)
        .scalar_subquery()
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

    ti_count = _ticket_instance_count_subquery()

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

    ti_count = _ticket_instance_count_subquery()

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
