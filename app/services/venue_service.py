from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.venues.models import Venue, Sector, Seat
from app.domain.venues.schemas import VenueCreateDTO, VenueUpdateDTO, SectorCreateDTO, SectorUpdateDTO, SeatCreateDTO, \
    SeatBulkCreateDTO, SeatUpdateDTO
from app.domain.venues import crud
from app.services.address_service import get_address


def _check_sector_allows_seats(sector: Sector) -> None:
    if sector.is_ga:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sector is GA - seats not allowed")


async def get_venue(db: AsyncSession, venue_id: int) -> Venue:
    venue = await crud.get_venue_by_id(db, venue_id)
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    return venue


async def list_venues(db: AsyncSession) -> list[Venue]:
    return await crud.list_all_venues(db)


async def create_venue(db: AsyncSession, schema: VenueCreateDTO) -> Venue:
    await get_address(db, schema.address_id)
    data = schema.model_dump(exclude_none=True)
    venue = await crud.create_venue(db, data)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Venue with this address already exists") from e
    return venue


async def update_venue(db: AsyncSession, schema: VenueUpdateDTO, venue_id: int) -> Venue:
    venue = await get_venue(db, venue_id)
    data = schema.model_dump(exclude_none=True)
    venue = await crud.update_venue(venue, data)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Venue with this address already exists") from e
    return venue


async def get_sector(db: AsyncSession, sector_id: int) -> Sector:
    sector = await crud.get_sector_by_id(db, sector_id)
    if not sector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found")
    return sector


async def list_sectors_by_venue(db: AsyncSession, venue_id: int) -> list[Sector]:
    return await crud.list_sectors_by_venue(db, venue_id)


async def create_sector(db: AsyncSession, venue_id: int, schema: SectorCreateDTO) -> Sector:
    await get_venue(db, venue_id)
    data = schema.model_dump(exclude_none=True)
    data["venue_id"] = venue_id
    sector = await crud.create_sector(db, data)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Sector name already in use for this venue") from e
    return sector


async def update_sector(db: AsyncSession, schema: SectorUpdateDTO, sector_id: int) -> Sector:
    sector = await get_sector(db, sector_id)
    data = schema.model_dump(exclude_none=True)
    sector = await crud.update_sector(sector, data)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Sector name already in use for this venue") from e
    return sector


async def get_seat(db: AsyncSession, seat_id: int) -> Seat:
    seat = await crud.get_seat_by_id(db, seat_id)
    if not seat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    return seat


async def list_seats_by_sector(db: AsyncSession, sector_id: int) -> list[Seat]:
    return await crud.list_seats_by_sector(db, sector_id)


async def create_seat(db: AsyncSession, schema: SeatCreateDTO, sector_id: int) -> Seat:
    sector = await get_sector(db, sector_id)
    _check_sector_allows_seats(sector)
    data = schema.model_dump(exclude_none=True)
    data["sector_id"] = sector_id
    seat = await crud.create_seat(db, data)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat already exists") from e
    return seat


async def bulk_create_seats(db: AsyncSession, schema: SeatBulkCreateDTO, sector_id: int) -> None:
    sector = await get_sector(db, sector_id)
    _check_sector_allows_seats(sector)
    seats = [s.model_dump(exclude_none=True) for s in schema.seats]
    await crud.bulk_add_seats(db, sector.id, seats)


async def update_seat(db: AsyncSession, schema: SeatUpdateDTO, seat_id: int) -> Seat:
    seat = await get_seat(db, seat_id)
    sector = await get_sector(db, seat.sector_id)
    _check_sector_allows_seats(sector)
    data = schema.model_dump(exclude_none=True)
    seat = await crud.update_seat(seat, data)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat already exists") from e
    return seat


async def delete_seat(db: AsyncSession, seat_id: int) -> None:
    seat = await get_seat(db, seat_id)
    await crud.delete_seat(db, seat)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat in use")
