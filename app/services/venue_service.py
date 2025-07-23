from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.venues.models import Venue, Sector
from app.domain.venues.schemas import VenueCreateDTO, VenueUpdateDTO, SectorCreateDTO, SectorUpdateDTO
from app.domain.venues import crud
from app.services.address_service import get_address
from app.core.db_utils import commit_or_409


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
    await commit_or_409(db, "Venue with this address already exists")
    return venue


async def update_venue(db: AsyncSession, schema: VenueUpdateDTO, venue_id: int) -> Venue:
    venue = await get_venue(db, venue_id)
    data = schema.model_dump(exclude_none=True)
    venue = await crud.update_venue(venue, data)
    await commit_or_409(db, "Venue with this address already exists")
    return venue


async def get_sector(db: AsyncSession, sector_id: int) -> Sector:
    sector = await crud.get_sector_by_id(db, sector_id)
    if not sector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found")
    return sector


async def list_sectors_by_venue(db: AsyncSession, venue_id: int) -> list[Sector]:
    return await crud.list_sectors_by_venue(db, venue_id)


async def create_sector(db: AsyncSession, venue_id: int, schema: SectorCreateDTO) -> Sector:
    await get_venue(db, schema.venue_id)
    data = schema.model_dump(exclude_none=True)
    data["venue_id"] = venue_id
    sector = await crud.create_sector(db, data)
    await commit_or_409(db, "Sector name already in use for this venue")
    return sector


async def update_sector(db: AsyncSession, schema: SectorUpdateDTO, sector_id: int) -> Sector:
    sector = await get_sector(db, sector_id)
    data = schema.model_dump(exclude_none=True)
    sector = await crud.update_sector(sector, data)
    await commit_or_409(db, "Sector name already in use for this venue")
    return sector

