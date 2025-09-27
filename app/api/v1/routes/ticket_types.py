from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from typing import Annotated
from app.domain.pricing.schemas import TicketTypeReadDTO, TicketTypeCreateDTO
from app.core.dependencies.auth import get_current_user_with_roles
from app.services import ticket_type_service


router = APIRouter(prefix="/ticket-types", tags=["ticket-types"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{ticket_type_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketTypeReadDTO,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_ticket_type(ticket_type_id: int, db: db_dependency):
    ticket_type = await ticket_type_service.get_ticket_type(db, ticket_type_id)
    return ticket_type


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[TicketTypeReadDTO],
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def list_ticket_types(db: db_dependency):
    return await ticket_type_service.list_ticket_types(db)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketTypeReadDTO,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def create_ticket_type(db: db_dependency, schema: TicketTypeCreateDTO, response: Response):
    ticket_type = await ticket_type_service.create_ticket_type(db, schema)
    response.headers["Location"] = f"{router.prefix}/{ticket_type.id}"
    return ticket_type


@router.delete(
    "/{ticket_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def delete_ticket_type(ticket_type_id: int, db: db_dependency):
    await ticket_type_service.delete_ticket_type(db, ticket_type_id)
