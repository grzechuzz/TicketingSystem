from app.services import venue_service
from fastapi import APIRouter, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.auth import get_current_user_with_roles
from app.domain.venues.schemas import SeatUpdateDTO, SeatReadDTO
from app.domain.users.models import User
from typing import Annotated


router = APIRouter(prefix='/seats', tags=['seats'])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{seat_id}",
    status_code=status.HTTP_200_OK,
    response_model=SeatReadDTO,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_seat(seat_id: int, db: db_dependency):
    return await venue_service.get_seat(db, seat_id)


@router.patch(
    "/{seat_id}",
    status_code=status.HTTP_200_OK,
    response_model=SeatReadDTO
)
async def update_seat(
        seat_id: int,
        model: SeatUpdateDTO,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN"))],
        request: Request
):
    return await venue_service.update_seat(db, model, seat_id, user, request)


@router.delete(
    "/{seat_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_seat(
        seat_id: int,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN"))],
        request: Request
):
    return await venue_service.delete_seat(db, seat_id, user, request)
