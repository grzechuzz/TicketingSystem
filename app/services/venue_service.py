from fastapi import HTTPException, status, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import PageDTO
from app.core.auditing import AuditSpan
from app.domain.users.models import User
from app.domain.venues.models import Venue, Sector, Seat
from app.domain.venues.schemas import VenueCreateDTO, VenueUpdateDTO, SectorCreateDTO, SectorUpdateDTO, SeatCreateDTO, \
    SeatBulkCreateDTO, SeatUpdateDTO, VenuesQueryDTO, VenueReadDTO
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


async def list_venues(db: AsyncSession, query: VenuesQueryDTO) -> PageDTO[VenueReadDTO]:
    venues, total = await crud.list_all_venues(db, query.page, query.page_size, name=query.name)
    items = [VenueReadDTO.model_validate(venue) for venue in venues]
    return PageDTO(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


async def create_venue(db: AsyncSession, schema: VenueCreateDTO, user: User, request: Request) -> Venue:
    async with AuditSpan(
        request,
        scope="VENUES",
        action="CREATE",
        user=user,
        object_type="venue",
        meta={"address_id": schema.address_id}
    ) as span:
        await get_address(db, schema.address_id)
        data = schema.model_dump(exclude_none=True)
        venue = await crud.create_venue(db, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Venue with this address already exists") from e
        span.object_id = venue.id
        return venue


async def update_venue(db: AsyncSession, schema: VenueUpdateDTO, venue_id: int, user: User, request: Request) -> Venue:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="VENUES",
        action="UPDATE",
        user=user,
        object_type="venue",
        object_id=venue_id,
        meta={"fields": fields}
    ):
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


async def create_sector(
        db: AsyncSession,
        venue_id: int,
        schema: SectorCreateDTO,
        user: User,
        request: Request
) -> Sector:
    async with AuditSpan(
        request,
        scope="SECTORS",
        action="CREATE",
        user=user,
        object_type="sector",
        meta={"venue_id": venue_id, "is_ga": schema.is_ga, "base_capacity": schema.base_capacity}
    ) as span:
        await get_venue(db, venue_id)
        data = schema.model_dump(exclude_none=True)
        data["venue_id"] = venue_id
        sector = await crud.create_sector(db, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Sector name already in use for this venue") from e
        span.object_id = sector.id
        return sector


async def update_sector(
        db: AsyncSession,
        schema: SectorUpdateDTO,
        sector_id: int,
        user: User,
        request: Request
) -> Sector:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="SECTORS",
        action="UPDATE",
        user=user,
        object_type="sector",
        object_id=sector_id,
        meta={"fields": fields}
    ):
        sector = await get_sector(db, sector_id)
        data = schema.model_dump(exclude_none=True)
        sector = await crud.update_sector(sector, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sector name already in use for this venue") from e
        return sector


async def get_seat(db: AsyncSession, seat_id: int) -> Seat:
    seat = await crud.get_seat_by_id(db, seat_id)
    if not seat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found")
    return seat


async def list_seats_by_sector(db: AsyncSession, sector_id: int) -> list[Seat]:
    return await crud.list_seats_by_sector(db, sector_id)


async def create_seat(db: AsyncSession, schema: SeatCreateDTO, sector_id: int, user: User, request: Request) -> Seat:
    async with AuditSpan(
        request,
        scope="SEATS",
        action="CREATE",
        user=user,
        object_type="seat",
        meta={"sector_id": sector_id, "row": schema.row, "number": schema.number}
    ) as span:
        sector = await get_sector(db, sector_id)
        _check_sector_allows_seats(sector)
        data = schema.model_dump(exclude_none=True)
        data["sector_id"] = sector_id
        seat = await crud.create_seat(db, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat already exists") from e
        span.object_id = seat.id
        return seat


async def bulk_create_seats(
        db: AsyncSession,
        schema: SeatBulkCreateDTO,
        sector_id: int,
        user: User,
        request: Request
) -> None:
    async with AuditSpan(
        request,
        scope="SEATS",
        action="CREATE_BULK",
        user=user,
        object_type="seat",
        meta={"sector_id": sector_id, "count": len(schema.seats)}
    ):
        sector = await get_sector(db, sector_id)
        _check_sector_allows_seats(sector)
        seats = [s.model_dump(exclude_none=True) for s in schema.seats]
        await crud.bulk_add_seats(db, sector.id, seats)


async def update_seat(
        db: AsyncSession,
        schema: SeatUpdateDTO,
        seat_id: int,
        user: User,
        request: Request
) -> Seat:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="SEATS",
        action="UPDATE",
        user=user,
        object_type="seat",
        object_id=seat_id,
        meta={"fields": fields}
    ):
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


async def delete_seat(db: AsyncSession, seat_id: int, user: User, request: Request) -> None:
    async with AuditSpan(
        request,
        scope="SEATS",
        action="DELETE",
        user=user,
        object_type="seat",
        object_id=seat_id
    ):
        seat = await get_seat(db, seat_id)
        await crud.delete_seat(db, seat)
        try:
            await db.flush()
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Seat in use")
