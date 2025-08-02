from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Event, EventStatus
from typing import Iterable


async def get_event_by_id(db: AsyncSession, event_id: int) -> Event | None:
    stmt = select(Event).where(Event.id == event_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_events(
        db: AsyncSession,
        *,
        statuses: Iterable[EventStatus] | None = None,
        organizer_ids: Iterable[int] | None = None
) -> list[Event]:
    stmt = select(Event)
    if statuses is not None:
        stmt = stmt.where(Event.status.in_(statuses))
    if organizer_ids is not None:
        stmt = stmt.where(Event.organizer_id.in_(organizer_ids))
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_event(db: AsyncSession, data: dict) -> Event:
    event = Event(**data)
    db.add(event)
    return event


async def update_event(event: Event, data: dict) -> Event:
    for k, v in data.items():
        setattr(event, k, v)
    return event
