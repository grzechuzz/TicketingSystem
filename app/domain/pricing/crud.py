from app.domain.pricing.models import TicketType, EventTicketType
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def get_ticket_type(db: AsyncSession, ticket_type_id: int) -> TicketType | None:
    stmt = select(TicketType).where(TicketType.id == ticket_type_id)
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


async def delete_ticket_type(db: AsyncSession, ticket_type: TicketType) -> None:
    await db.delete(ticket_type)


async def get_event_ticket_type(db: AsyncSession, event_ticket_type_id: int) -> EventTicketType | None:
    stmt = select(EventTicketType).where(EventTicketType.id == event_ticket_type_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_event_ticket_types_by_sector(db: AsyncSession, event_sector_id: int) -> list[EventTicketType]:
    stmt = select(EventTicketType).where(EventTicketType.event_sector_id == event_sector_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_event_ticket_type(db: AsyncSession, data: dict) -> EventTicketType:
    event_ticket_type = EventTicketType(**data)
    db.add(event_ticket_type)
    return event_ticket_type


async def bulk_add_event_ticket_types(db: AsyncSession, event_sector_id: int, data: list[dict]) -> None:
    stmt = (insert(EventTicketType).values([{"event_sector_id": event_sector_id, **d} for d in data])
            .on_conflict_do_nothing())
    await db.execute(stmt)


async def update_event_ticket_type(event_ticket_type: EventTicketType, data: dict) -> EventTicketType:
    for key, value in data.items():
        setattr(event_ticket_type, key, value)
    return event_ticket_type


async def delete_event_ticket_type(db: AsyncSession, event_ticket_type: EventTicketType) -> None:
    await db.delete(event_ticket_type)
