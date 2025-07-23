from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Event


async def get_event_by_id(db: AsyncSession, event_id: int) -> Event | None:
    stmt = select(Event).where(Event.id == event_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_all_events(db: AsyncSession) -> list[Event]:
    stmt = select(Event)
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
