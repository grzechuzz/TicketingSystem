from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.domain import Venue, Sector, Seat


async def get_venue_by_id(db: AsyncSession, venue_id: int) -> Venue | None:
    stmt = select(Venue).where(Venue.id == venue_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_all_venues(db: AsyncSession) -> list[Venue]:
    stmt = select(Venue)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_venue(db: AsyncSession, data: dict) -> Venue:
    venue = Venue(**data)
    db.add(venue)
    return venue


async def update_venue(venue: Venue, data: dict) -> Venue:
    for key, value in data.items():
        setattr(venue, key, value)
    return venue


async def get_sector_by_id(db: AsyncSession, sector_id: int) -> Sector | None:
    stmt = select(Sector).where(Sector.id == sector_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_sectors_by_venue(db: AsyncSession, venue_id: int) -> list[Sector]:
    stmt = select(Sector).where(Sector.venue_id == venue_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_sector(db: AsyncSession, data: dict) -> Sector:
    sector = Sector(**data)
    db.add(sector)
    return sector


async def update_sector(sector: Sector, data: dict) -> Sector:
    for key, value in data.items():
        setattr(sector, key, value)
    return sector


async def get_seat_by_id(db: AsyncSession, seat_id: int) -> Seat | None:
    stmt = select(Seat).where(Seat.id == seat_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_seats_by_sector(db: AsyncSession, sector_id: int) -> list[Seat]:
    stmt = select(Seat).where(Seat.sector_id == sector_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_seat(db: AsyncSession, data: dict) -> Seat:
    seat = Seat(**data)
    db.add(seat)
    return seat


async def bulk_add_seats(db: AsyncSession, sector_id: int, data: list[dict]) -> None:
    stmt = insert(Seat).values([{"sector_id": sector_id, **d} for d in data]).on_conflict_do_nothing()
    await db.execute(stmt)


async def update_seat(seat: Seat, data: dict) -> Seat:
    for key, value in data.items():
        setattr(seat, key, value)
    return seat


async def delete_seat(db: AsyncSession, seat: Seat) -> None:
    await db.delete(seat)
