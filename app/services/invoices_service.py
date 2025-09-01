from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.core.pagination import PageDTO
from app.domain.booking.counters import invoice_counters
from app.domain.booking.models import Invoice, Order, TicketInstance
from app.domain.booking.schemas import UserInvoicesQueryDTO, InvoiceListItemDTO, InvoiceDetailsDTO, InvoiceLineDTO, \
    AdminInvoicesQueryDTO, AdminInvoiceListItemDTO
from app.domain.users.models import User
from app.domain.events.models import Event
from typing import Iterable, Callable, Any


TZ = ZoneInfo("Europe/Warsaw")


async def _next_invoice_number(db: AsyncSession, paid_at_utc: datetime) -> str:
    year = paid_at_utc.astimezone(TZ).year
    row = await db.execute(
        insert(invoice_counters)
        .values(fiscal_year=year, counter=1)
        .on_conflict_do_update(
            index_elements=[invoice_counters.c.fiscal_year],
            set_={"counter": invoice_counters.c.counter + 1},
        )
        .returning(invoice_counters.c.counter)
    )
    n = row.scalar_one()
    return f"{year}-{n:08d}"


async def issue_invoice_for_order(db: AsyncSession, order: Order, paid_at_utc: datetime) -> Invoice | None:
    invoice = order.invoice
    if not invoice:
        return None
    if invoice.issued_at is None:
        invoice.issued_at = paid_at_utc
    if invoice.invoice_number is None:
        invoice.invoice_number = await _next_invoice_number(db, paid_at_utc)
    return invoice


def _ti_agg_subquery():
    ti_agg = (
        select(
            TicketInstance.order_id.label("order_id"),
            func.count(TicketInstance.id).label("items_count"),
            func.coalesce(func.sum(TicketInstance.price_net_snapshot), 0).label("total_net"),
            func.coalesce(func.sum(TicketInstance.price_gross_snapshot), 0).label("total_gross"),
        )
        .group_by(TicketInstance.order_id)
        .subquery("ti_agg")
    )
    return ti_agg


async def _list_invoices_helper[T](
        db: AsyncSession,
        where: Iterable,
        page: int,
        page_size: int,
        join_user: bool,
        row_mapper: Callable[[Any], T]
) -> PageDTO[T]:
    ti_agg = _ti_agg_subquery()

    total_stmt = select(func.count()).select_from(Invoice).join(Order)

    if join_user:
        total_stmt = total_stmt.join(User)
    total = await db.scalar(total_stmt.where(*where))

    row_stmt = (
        select(
            Invoice.id,
            Invoice.invoice_number,
            Invoice.order_id,
            Invoice.issued_at,
            ti_agg.c.items_count,
            ti_agg.c.total_net,
            (ti_agg.c.total_gross - ti_agg.c.total_net).label("total_vat"),
            ti_agg.c.total_gross
        )
        .select_from(Invoice)
        .join(Order)
        .join(ti_agg, ti_agg.c.order_id == Order.id)
    )

    if join_user:
        row_stmt = row_stmt.add_columns(
            User.id.label("user_id"),
            User.email.label("user_email")
        ).join(User)

    row_stmt = (
        row_stmt.where(*where)
        .order_by(Invoice.issued_at.desc().nulls_last(), Invoice.id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )

    rows = await db.execute(row_stmt)
    items = [row_mapper(r) for r in rows.all()]

    return PageDTO[T](
        items=items,
        total=int(total or 0),
        page=page,
        page_size=page_size
    )


def _map_user_invoice_row(r) -> InvoiceListItemDTO:
    return InvoiceListItemDTO(
        id=r.id,
        invoice_number=r.invoice_number,
        order_id=r.order_id,
        issued_at=r.issued_at,
        items_count=int(r.items_count or 0),
        total_net=r.total_net,
        total_vat=r.total_vat,
        total_gross=r.total_gross
    )


def _map_admin_invoice_row(r) -> AdminInvoiceListItemDTO:
    return AdminInvoiceListItemDTO(
        id=r.id,
        invoice_number=r.invoice_number,
        order_id=r.order_id,
        issued_at=r.issued_at,
        items_count=int(r.items_count or 0),
        total_net=r.total_net,
        total_vat=r.total_vat,
        total_gross=r.total_gross,
        user_id=r.user_id,
        user_email=r.user_email
    )


async def _get_invoice_and_order_id(
        db: AsyncSession,
        invoice_id: int,
        extra_filters: list
) -> tuple[Invoice, int]:
    row = await db.execute(
        select(Invoice, Order.id.label("order_id"))
        .select_from(Invoice)
        .join(Order)
        .where(Invoice.id == invoice_id, Invoice.issued_at.is_not(None), *extra_filters)
    )
    result = row.first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    invoice, order_id = result
    return invoice, order_id


async def _build_invoice_details(
        db: AsyncSession,
        invoice: Invoice,
        order_id: int
) -> InvoiceDetailsDTO:
    lines_invoice = await db.execute(
        select(
            func.count(TicketInstance.id).label("quantity"),
            Event.name.label("event_name"),
            TicketInstance.ticket_type_name_snapshot.label("ticket_type_name"),
            TicketInstance.vat_rate_snapshot.label("vat_rate"),
            TicketInstance.price_net_snapshot.label("unit_price_net"),
            TicketInstance.price_gross_snapshot.label("unit_price_gross"),
            func.sum(TicketInstance.price_net_snapshot).label("line_net"),
            func.sum(TicketInstance.price_gross_snapshot).label("line_gross")
        )
        .select_from(TicketInstance)
        .join(Event)
        .where(TicketInstance.order_id == order_id)
        .group_by(
            Event.name,
            TicketInstance.ticket_type_name_snapshot,
            TicketInstance.vat_rate_snapshot,
            TicketInstance.price_net_snapshot,
            TicketInstance.price_gross_snapshot
        )
        .order_by(Event.name, TicketInstance.ticket_type_name_snapshot)
    )

    items = []
    total_net = Decimal("0.00")
    total_gross = Decimal("0.00")

    for r in lines_invoice.all():
        line_vat = (r.line_gross or Decimal("0.00")) - (r.line_net or Decimal("0.00"))
        items.append(
            InvoiceLineDTO(
                event_name=r.event_name,
                ticket_type_name=r.ticket_type_name,
                quantity=int(r.quantity),
                vat_rate=r.vat_rate,
                unit_price_net=r.unit_price_net,
                unit_price_gross=r.unit_price_gross,
                line_net=r.line_net,
                line_vat=line_vat,
                line_gross=r.line_gross
            )
        )
        total_net += r.line_net or Decimal("0.00")
        total_gross += r.line_gross or Decimal("0.00")

    total_vat = total_gross - total_net

    return InvoiceDetailsDTO(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        currency_code=invoice.currency_code,
        invoice_type=invoice.invoice_type,
        full_name=invoice.full_name,
        company_name=invoice.company_name,
        tax_id=invoice.tax_id,
        street=invoice.street,
        postal_code=invoice.postal_code,
        city=invoice.city,
        country_code=invoice.country_code,
        created_at=invoice.created_at,
        issued_at=invoice.issued_at,
        order_id=order_id,
        items=items,
        total_gross=total_gross,
        total_net=total_net,
        total_vat=total_vat
    )


async def list_user_invoices(
        db: AsyncSession,
        user: User,
        query: UserInvoicesQueryDTO
) -> PageDTO[InvoiceListItemDTO]:
    where = [Order.user_id == user.id, Invoice.issued_at.is_not(None)]
    return await _list_invoices_helper(
        db=db,
        where=where,
        page=query.page,
        page_size=query.page_size,
        join_user=False,
        row_mapper=_map_user_invoice_row
    )


async def get_user_invoice_details(db: AsyncSession, user: User, invoice_id: int) -> InvoiceDetailsDTO:
    invoice, order_id = await _get_invoice_and_order_id(db, invoice_id, [Order.user_id == user.id])
    return await _build_invoice_details(db, invoice, order_id)


async def list_admin_invoices(db: AsyncSession, query: AdminInvoicesQueryDTO) -> PageDTO[AdminInvoiceListItemDTO]:
    where = [Invoice.issued_at.is_not(None)]
    if query.user_id is not None:
        where.append(Order.user_id == query.user_id)
    if query.email is not None:
        where.append(func.lower(User.email) == func.lower(query.email))
    if query.invoice_type is not None:
        where.append(Invoice.invoice_type == query.invoice_type)

    return await _list_invoices_helper(
        db=db,
        where=where,
        page=query.page,
        page_size=query.page_size,
        join_user=True,
        row_mapper=_map_admin_invoice_row
    )


async def get_invoice_details_admin(
        db: AsyncSession,
        invoice_id: int
) -> InvoiceDetailsDTO:
    invoice, order_id = await _get_invoice_and_order_id(db, invoice_id, [])
    return await _build_invoice_details(db, invoice, order_id)
