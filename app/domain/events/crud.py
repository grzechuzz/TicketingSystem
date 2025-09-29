from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Event, EventStatus
from typing import Iterable
from app.core.pagination import paginate


async def get_event_by_id(db: AsyncSession, event_id: int) -> Event | None:
    stmt = select(Event).where(Event.id == event_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_events(
        db: AsyncSession,
        page: int,
        page_size: int,
        *,
        statuses: Iterable[EventStatus] | None = None,
        organizer_ids: Iterable[int] | None = None,
        venue_id: int | None = None,
        name: str | None = None,
        date_from=None,
        date_to=None,
) -> tuple[list[Event], int]:
    stmt = select(Event)
    where = []

    if statuses is not None:
        where.append(Event.status.in_(statuses))
    if organizer_ids is not None:
        where.append(Event.organizer_id.in_(organizer_ids))
    if venue_id is not None:
        where.append(Event.venue_id == venue_id)
    if name:
        where.append(Event.name.ilike(f"%{name}%"))
    if date_from is not None:
        where.append(Event.event_start >= date_from)
    if date_to is not None:
        where.append(Event.event_start <= date_to)

    items, total = await paginate(
        db,
        base_stmt=stmt,
        page=page,
        page_size=page_size,
        where=where,
        order_by=[Event.event_start.desc(), Event.id],
        scalars=True,
        count_by=Event.id
    )

    return items, total


async def create_event(db: AsyncSession, data: dict) -> Event:
    event = Event(**data)
    db.add(event)
    return event


async def update_event(event: Event, data: dict) -> Event:
    for k, v in data.items():
        setattr(event, k, v)
    return event
