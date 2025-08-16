from fastapi import APIRouter, Depends, Response, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.users.models import User
from app.services import booking_service
from app.domain.booking.schemas import OrderDetailsDTO

router = APIRouter(prefix="/users", tags=["users"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.get(
    "/me/orders/pending",
    status_code=status.HTTP_200_OK,
    response_model=OrderDetailsDTO,
    response_model_exclude_none=True
)
async def get_user_pending_order(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER", "ADMIN"))]
):
    order = await booking_service.get_user_pending_order(db, user)
    return OrderDetailsDTO.model_validate(order)


@router.delete(
    "/me/orders/items/{ticket_instance_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_item_from_pending_order(
        ticket_instance_id: int,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER", "ADMIN"))]
):
    await booking_service.remove_ticket_instance(db, user, ticket_instance_id)