from app.domain.allocation.models import EventSector
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def get_event_sector(db: AsyncSession, event_id: int, sector_id: int) -> EventSector | None:
    stmt = select(EventSector).where(EventSector.event_id == event_id, EventSector.sector_id == sector_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_event_sectors(db: AsyncSession, event_id: int) -> list[EventSector]:
    stmt = select(EventSector).where(EventSector.event_id == event_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_event_sector(db: AsyncSession, data: dict) -> EventSector:
    event_sector = EventSector(**data)
    db.add(event_sector)
    return event_sector


async def bulk_add_event_sectors(db: AsyncSession, event_id: int, data: list[dict]) -> None:
    stmt = insert(EventSector).values([{"event_id": event_id, **d} for d in data]).on_conflict_do_nothing()
    await db.execute(stmt)


async def delete_event_sector(db: AsyncSession, event_sector: EventSector) -> None:
    await db.delete(event_sector)
