from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.event_catalog.models import TicketType
from app.domain.event_catalog import crud
from app.domain.event_catalog.schemas import TicketTypeCreateDTO


async def get_ticket_type(db: AsyncSession, ticket_type_id: int) -> TicketType:
    ticket_type = await crud.get_ticket_type(db, ticket_type_id)
    if not ticket_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket type not found")
    return ticket_type


async def list_ticket_types(db: AsyncSession) -> list[TicketType]:
    return await crud.list_ticket_types(db)


async def create_ticket_type(db: AsyncSession, schema: TicketTypeCreateDTO) -> TicketType:
    data = schema.model_dump(exclude_none=True)
    ticket_type = await crud.create_ticket_type(db, data)

    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ticket type already exists")
    return ticket_type


async def delete_ticket_type(db: AsyncSession, ticket_type_id: int) -> None:
    ticket_type = await get_ticket_type(db, ticket_type_id)
    await crud.delete_ticket_type(db, ticket_type)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ticket type in use")
