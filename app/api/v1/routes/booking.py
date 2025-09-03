from fastapi import APIRouter, Depends, Response, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.users.models import User
from app.services import booking_service
from app.domain.booking.schemas import ReserveTicketRequestDTO, ReserveTicketReadDTO


router = APIRouter(prefix="/events/{event_id}/reservations", tags=["booking"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ReserveTicketReadDTO,
    response_model_exclude_none=True,
)
async def reserve_ticket(
        event_id: int,
        schema: ReserveTicketRequestDTO,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER", "ADMIN"))],
        response: Response,
):
    order, ticket_instance = await booking_service.reserve_ticket(
        db=db,
        user=user,
        event_id=event_id,
        event_ticket_type_id=schema.event_ticket_type_id,
        seat_id=schema.seat_id,
    )

    response.headers["Location"] = f"/users/me/orders/{order.id}"

    return ReserveTicketReadDTO(
        order_id=order.id,
        ticket_instance_id=ticket_instance.id,
        reserved_until=order.reserved_until,
        order_total_price=order.total_price,
    )
