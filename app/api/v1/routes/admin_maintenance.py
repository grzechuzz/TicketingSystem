from fastapi import APIRouter, Depends, status, Query
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.services.booking_service import cleanup_expired_reservations
from pydantic import BaseModel


class CleanupStatsDTO(BaseModel):
    orders_cancelled: int
    tickets_released: int
    ga_released: int


router = APIRouter(prefix="/admin/maintenance", tags=["admin-maintenance"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/cleanup-expired",
    status_code=status.HTTP_200_OK,
    response_model=CleanupStatsDTO,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def cleanup(db: db_dependency, limit: int = Query(500, ge=1, le=5000)):
    return await cleanup_expired_reservations(db, limit=limit)
