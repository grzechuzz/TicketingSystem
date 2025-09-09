from typing import Iterable, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import PageDTO, paginate
from app.domain.users.models import User
from app.domain.events.models import Event
from app.domain.venues.models import Venue, Sector, Seat
from app.domain.allocation.models import EventSector
from app.domain.pricing.models import EventTicketType
from app.domain.booking.models import Order, TicketInstance, Ticket, TicketHolder
from app.domain.booking.schemas import TicketReadItemDTO, TicketHolderPublicDTO, TicketHolderPrivateDTO, \
    UserTicketsQueryDTO, OrganizerTicketsQueryDTO, AdminTicketsQueryDTO


def _to_holder_dto(row: Any, full: bool):
    if row.holder_id is None:
        return None

    if full:
        return TicketHolderPrivateDTO(
            id=row.holder_id,
            first_name=row.first_name,
            last_name=row.last_name,
            identification_number=row.identification_number or ""
        )

    suffix = (row.identification_number or "")[-4:]
    return TicketHolderPublicDTO(
        id=row.holder_id,
        first_name=row.first_name,
        last_name=row.last_name,
        identification_suffix=suffix
    )


def _ticket_row_select():
    return (
        select(
            Ticket.id,
            Ticket.code,
            Ticket.status,
            Ticket.created_at,
            Event.id.label("event_id"),
            Event.name.label("event_name"),
            Event.event_start,
            Venue.name.label("venue_name"),
            Sector.is_ga,
            Sector.name.label("sector_name"),
            Seat.row,
            Seat.number.label("seat"),
            TicketInstance.ticket_type_name_snapshot.label("ticket_type_name"),
            TicketInstance.price_gross_snapshot.label("price_gross"),
            TicketHolder.id.label("holder_id"),
            TicketHolder.first_name,
            TicketHolder.last_name,
            TicketHolder.identification_number
        )
        .select_from(Ticket)
        .join(TicketInstance, TicketInstance.id == Ticket.ticket_instance_id)
        .join(Order, Order.id == TicketInstance.order_id)
        .join(Event, Event.id == TicketInstance.event_id)
        .join(Venue, Venue.id == Event.venue_id)
        .join(EventTicketType, EventTicketType.id == TicketInstance.event_ticket_type_id)
        .join(EventSector, EventSector.id == EventTicketType.event_sector_id)
        .join(Sector, Sector.id == EventSector.sector_id)
        .outerjoin(Seat, Seat.id == TicketInstance.seat_id)
        .outerjoin(TicketHolder, TicketHolder.ticket_instance_id == TicketInstance.id)
    )


def _map_ticket_row(row: Any, full_holder: bool) -> TicketReadItemDTO:
    return TicketReadItemDTO(
        id=row.id,
        code=row.code,
        status=row.status,
        created_at=row.created_at,
        event_id=row.event_id,
        event_name=row.event_name,
        event_start=row.event_start,
        venue_name=row.venue_name,
        is_ga=row.is_ga,
        sector_name=row.sector_name,
        row=row.row,
        seat=row.seat,
        ticket_type_name=row.ticket_type_name,
        price_gross=row.price_gross,
        holder=_to_holder_dto(row, full_holder)
    )


async def _list_tickets_helper(
        db: AsyncSession,
        where: Iterable,
        page: int,
        page_size: int,
        *,
        needs_user_join: bool,
        full_holder: bool
) -> PageDTO[TicketReadItemDTO]:
    base = _ticket_row_select()
    if needs_user_join:
        base = base.join(User, User.id == Order.user_id)

    rows, total = await paginate(
        db,
        base_stmt=base,
        page=page,
        page_size=page_size,
        where=where,
        order_by=[Ticket.created_at.desc(), Ticket.id],
        scalars=False,
        count_by=Ticket.id
    )

    items = [_map_ticket_row(r, full_holder=full_holder) for r in rows]

    return PageDTO[TicketReadItemDTO](
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


async def list_user_tickets(
        db: AsyncSession,
        user: User,
        query: UserTicketsQueryDTO
) -> PageDTO[TicketReadItemDTO]:
    where = [Order.user_id == user.id]
    if query.status is not None:
        where.append(Ticket.status == query.status)

    return await _list_tickets_helper(
        db=db,
        where=where,
        page=query.page,
        page_size=query.page_size,
        needs_user_join=False,
        full_holder=True
    )


async def list_organizer_tickets(
        db: AsyncSession,
        organizer_id: int,
        query: OrganizerTicketsQueryDTO
) -> PageDTO[TicketReadItemDTO]:
    where = [Event.organizer_id == organizer_id]
    if query.status is not None:
        where.append(Ticket.status == query.status)
    if query.event_id is not None:
        where.append(Event.id == query.event_id)
    if query.ticket_id is not None:
        where.append(Ticket.id == query.ticket_id)
    if query.code is not None:
        where.append(Ticket.code == query.code)
    if query.email is not None:
        where.append(func.lower(User.email) == func.lower(query.email))

    return await _list_tickets_helper(
        db=db,
        where=where,
        page=query.page,
        page_size=query.page_size,
        needs_user_join=(query.email is not None),
        full_holder=False
    )


async def list_admin_tickets(
        db: AsyncSession,
        query: AdminTicketsQueryDTO
) -> PageDTO[TicketReadItemDTO]:
    where = []
    if query.status is not None:
        where.append(Ticket.status == query.status)
    if query.event_id is not None:
        where.append(Event.id == query.event_id)
    if query.ticket_id is not None:
        where.append(Ticket.id == query.ticket_id)
    if query.code is not None:
        where.append(Ticket.code == query.code)
    if query.email is not None:
        where.append(func.lower(User.email) == func.lower(query.email))
    if query.organizer_id is not None:
        where.append(Event.organizer_id == query.organizer_id)
    if query.user_id is not None:
        where.append(Order.user_id == query.user_id)

    return await _list_tickets_helper(
        db=db,
        where=where,
        page=query.page,
        page_size=query.page_size,
        needs_user_join=(query.email is not None),
        full_holder=False
    )
