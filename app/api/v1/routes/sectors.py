from app.services import venue_service
from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.venues.schemas import SectorReadDTO, SectorUpdateDTO, SeatReadDTO, SeatCreateDTO, SeatBulkCreateDTO
from typing import Annotated


router = APIRouter(prefix='/sectors', tags=['sectors'])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{sector_id}",
    status_code=status.HTTP_200_OK,
    response_model=SectorReadDTO,
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def get_sector(sector_id: int, db: db_dependency):
    sector = await venue_service.get_sector(db, sector_id)
    return sector


@router.patch(
    "/{sector_id}",
    status_code=status.HTTP_200_OK,
    response_model=SectorReadDTO,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def rename_sector(sector_id: int, schema: SectorUpdateDTO, db: db_dependency):
    return await venue_service.update_sector(db, schema, sector_id)


@router.post(
    "/{sector_id}/seats",
    status_code=status.HTTP_201_CREATED,
    response_model=SeatReadDTO,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def create_seat_for_sector(sector_id: int, schema: SeatCreateDTO, db: db_dependency, response: Response):
    seat = await venue_service.create_seat(db, schema, sector_id)
    response.headers["Location"] = f"/seats/{seat.id}"
    return seat


@router.post(
    "/{sector_id}/seats/bulk",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))],
)
async def bulk_add_seats_for_sector(sector_id: int, schema: SeatBulkCreateDTO, db: db_dependency):
    return await venue_service.bulk_create_seats(db, schema, sector_id)


@router.get(
    "/{sector_id}/seats",
    status_code=status.HTTP_200_OK,
    response_model=list[SeatReadDTO],
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_all_seats_by_sector(sector_id: int, db: db_dependency):
    return await venue_service.list_seats_by_sector(db, sector_id)
