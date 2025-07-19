from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain import Venue

async def get_by_id(db: AsyncSession, venue_id: int) -> Venue | None:
    stmt = select(Venue).where(Venue.id == venue_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def list_all(db: AsyncSession) -> list[Venue]:
    stmt = select(Venue)
    result = await db.execute(stmt)
    return result.scalars().all()

async def create(db: AsyncSession, data: dict) -> Venue:
    venue = Venue(**data)
    db.add(venue)
    return venue

async def update(venue: Venue, data: dict) -> Venue:
    for key, value in data.items():
        setattr(venue, key, value)
    return venue
