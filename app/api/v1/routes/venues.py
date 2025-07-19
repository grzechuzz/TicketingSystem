from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.services.venue_service import create_venue, get_venue, list_venues, update_venue
from app.domain.venues.schemas import VenueCreateDTO, VenueUpdateDTO, VenueReadDTO
from typing import Annotated

router = APIRouter(prefix='/venues', tags=['venues'])

db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=VenueReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles('ADMIN'))]
)
async def create(model: VenueCreateDTO, db: db_dependency, response: Response):
    venue = await create_venue(db, model)
    response.headers["Location"] = f"{router.prefix}/{venue.id}"
    return venue

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[VenueReadDTO]
)
async def get_all(db: db_dependency):
    venues = await list_venues(db)
    return venues

@router.get(
    "/{venue_id}",
    status_code=status.HTTP_200_OK,
    response_model=VenueReadDTO
)
async def get(venue_id: int, db: db_dependency):
    venue = await get_venue(db, venue_id)
    return venue

@router.put(
    "/{venue_id}",
    status_code=status.HTTP_200_OK,
    response_model=VenueReadDTO,
    dependencies=[Depends(get_current_user_with_roles('ADMIN'))]
)
async def update(
        model: VenueUpdateDTO,
        venue_id: int,
        db: db_dependency
):
    venue = await update_venue(db, model, venue_id)
    return venue
