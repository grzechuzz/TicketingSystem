from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.venues.models import Venue
from app.domain.venues.schemas import VenueCreateDTO, VenueUpdateDTO
from app.domain.venues import crud
from app.services.address_service import get_address

async def get_venue(db: AsyncSession, venue_id: int) -> Venue:
    venue = await crud.get_by_id(db, venue_id)
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    return venue

async def list_venues(db: AsyncSession) -> list[Venue]:
    return await crud.list_all(db)

async def create_venue(db: AsyncSession, schema: VenueCreateDTO) -> Venue:
    await get_address(db, schema.address_id)
    data = schema.model_dump(exclude_none=True)
    venue = await crud.create(db, data)
    await db.commit()
    return venue

async def update_venue(db: AsyncSession, schema: VenueUpdateDTO, venue_id: int) -> Venue:
    venue = await get_venue(db, venue_id)
    data = schema.model_dump(exclude_none=True)
    venue = await crud.update(venue, data)
    await db.commit()
    return venue
