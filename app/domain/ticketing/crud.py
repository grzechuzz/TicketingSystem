from app.domain.ticketing.models import EventSector, TicketType
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


async def get_ticket_type(db: AsyncSession, tt_id: int) -> TicketType | None:
    stmt = select(TicketType).where(TicketType.id == tt_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_ticket_types(db: AsyncSession) -> list[TicketType]:
    stmt = select(TicketType)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_ticket_type(db: AsyncSession, data: dict) -> TicketType:
    ticket_type = TicketType(**data)
    db.add(ticket_type)
    return ticket_type


async def delete_ticket_type(db: AsyncSession, tt: TicketType) -> None:
    await db.delete(tt)
