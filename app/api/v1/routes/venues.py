from app.core.pagination import PageDTO
from app.services import venue_service
from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.auth import get_current_user_with_roles
from app.domain.venues.schemas import (
    VenueCreateDTO,
    VenueUpdateDTO,
    VenueReadDTO,
    SectorReadDTO,
    SectorCreateDTO, VenuesQueryDTO
)
from typing import Annotated


router = APIRouter(prefix='/venues', tags=['venues'])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=VenueReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def create_venue(
        schema: VenueCreateDTO,
        db: db_dependency,
        response: Response
):
    venue = await venue_service.create_venue(db, schema)
    response.headers["Location"] = f"{router.prefix}/{venue.id}"
    return venue


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[VenueReadDTO],
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def get_all_venues(db: db_dependency, query: Annotated[VenuesQueryDTO, Depends()]):
    venues = await venue_service.list_venues(db, query)
    return venues


@router.get(
    "/{venue_id}",
    status_code=status.HTTP_200_OK,
    response_model=VenueReadDTO,
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def get_venue(venue_id: int, db: db_dependency):
    venue = await venue_service.get_venue(db, venue_id)
    return venue


@router.put(
    "/{venue_id}",
    status_code=status.HTTP_200_OK,
    response_model=VenueReadDTO,
    dependencies=[Depends(get_current_user_with_roles('ADMIN'))]
)
async def update_venue(
        venue_id: int,
        schema: VenueUpdateDTO,
        db: db_dependency
):
    venue = await venue_service.update_venue(db, schema, venue_id)
    return venue


@router.post(
    "/{venue_id}/sectors",
    status_code=status.HTTP_201_CREATED,
    response_model=SectorReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles('ADMIN'))],
    name="create_sector_for_venue"
)
async def create_sector_for_venue(
        venue_id: int,
        schema: SectorCreateDTO,
        db: db_dependency,
        response: Response,
):
    sector = await venue_service.create_sector(db, venue_id, schema)
    response.headers["Location"] = f"/sectors/{sector.id}"
    return sector


@router.get(
    "/{venue_id}/sectors",
    status_code=status.HTTP_200_OK,
    response_model=list[SectorReadDTO],
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def get_all_sectors_by_venue(venue_id: int, db: db_dependency):
    sectors = await venue_service.list_sectors_by_venue(db, venue_id)
    return sectors
