from fastapi import APIRouter, status, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles, require_event_ticket_type_access
from app.domain.pricing.schemas import EventTicketTypeReadDTO, EventTicketTypeUpdateDTO
from app.domain.pricing.models import EventTicketType
from app.services import event_ticket_type_service


router = APIRouter(prefix="/event-ticket-types", tags=["event-ticket-types"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{event_ticket_type_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventTicketTypeReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_event_ticket_type(event_ticket_type_id: int, db: db_dependency):
    return await event_ticket_type_service.get_event_ticket_type(db, event_ticket_type_id)


@router.patch(
    "/{event_ticket_type_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventTicketTypeReadDTO,
    response_model_exclude_none=True,
)
async def update_event_ticket_type(
        event_ticket_type: Annotated[EventTicketType, Depends(require_event_ticket_type_access)],
        schema: EventTicketTypeUpdateDTO,
        db: db_dependency
):
    return await event_ticket_type_service.update_event_ticket_type(db, event_ticket_type, schema)


@router.delete(
    "/{event_ticket_type_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_event_ticket_type(
        event_ticket_type: Annotated[EventTicketType, Depends(require_event_ticket_type_access)],
        db: db_dependency
):
    await event_ticket_type_service.delete_event_ticket_type(db, event_ticket_type)
