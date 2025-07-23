from app.services import venue_service
from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.venues.schemas import SectorReadDTO, SectorUpdateDTO

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
async def rename_sector(sector_id: int, model: SectorUpdateDTO, db: db_dependency):
    return await venue_service.update_sector(db, model, sector_id)
