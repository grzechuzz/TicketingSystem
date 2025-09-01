from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles, require_organizer_member
from app.core.pagination import PageDTO
from app.domain.users.models import User
from app.domain.booking.schemas import UserTicketsQueryDTO, OrganizerTicketsQueryDTO, AdminTicketsQueryDTO, \
    TicketReadItemDTO
from app.services import tickets_service


router = APIRouter(tags=["tickets"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/users/me/tickets",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[TicketReadItemDTO],
    response_model_exclude_none=True
)
async def list_user_tickets(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER"))],
        query: Annotated[UserTicketsQueryDTO, Depends()]
):
    return await tickets_service.list_user_tickets(db, user, query)


@router.get(
    "/organizers/{organizer_id}/tickets",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[TicketReadItemDTO],
    response_model_exclude_none=True
)
async def list_tickets_organizer(
        organizer_id: Annotated[int, Depends(require_organizer_member)],
        db: db_dependency,
        query: Annotated[OrganizerTicketsQueryDTO, Depends()]
):
    return await tickets_service.list_organizer_tickets(db, organizer_id, query)


@router.get(
    "/admin/tickets",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[TicketReadItemDTO],
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def list_tickets_admin(
        db: db_dependency,
        query: Annotated[AdminTicketsQueryDTO, Depends()]
):
    return await tickets_service.list_admin_tickets(db, query)
