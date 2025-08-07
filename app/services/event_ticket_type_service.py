from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.ticketing import crud
from app.domain.ticketing.schemas import EventTicketTypeCreateDTO, EventTicketTypeUpdateDTO, \
    EventTicketTypeBulkCreateDTO
from app.domain.ticketing.models import EventTicketType, EventSector


async def get_event_ticket_type(db: AsyncSession, event_ticket_type_id: int) -> EventTicketType:
    event_ticket_type = await crud.get_event_ticket_type(db, event_ticket_type_id)
    if not event_ticket_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event ticket type not found")
    return event_ticket_type


async def list_event_sector_ticket_types(db: AsyncSession, event_sector_id: int) -> list[EventTicketType]:
    return await crud.list_event_ticket_types_by_sector(db, event_sector_id)


async def create_event_ticket_type(
    db: AsyncSession,
    schema: EventTicketTypeCreateDTO,
    event_sector: EventSector
) -> EventTicketType:
    data = schema.model_dump(exclude_none=True)
    data["event_sector_id"] = event_sector.id

    event_ticket_type = await crud.create_event_ticket_type(db, data)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ticket type already defined for this sector"
        )
    return event_ticket_type


async def bulk_create_event_ticket_types(
    db: AsyncSession,
    schema: EventTicketTypeBulkCreateDTO,
    event_sector: EventSector
) -> None:
    data = [ett.model_dump(exclude_none=True) for ett in schema.event_ticket_types]
    await crud.bulk_add_event_ticket_types(db, event_sector.id, data)
    await db.commit()


async def update_event_ticket_type(
        db: AsyncSession,
        event_ticket_type_id: int,
        schema: EventTicketTypeUpdateDTO
) -> EventTicketType:
    event_ticket_type = await get_event_ticket_type(db, event_ticket_type_id)
    data = schema.model_dump(exclude_none=True)
    event_ticket_type = await crud.update_event_ticket_type(event_ticket_type, data)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ticket type already defined for this sector"
        )
    return event_ticket_type


async def delete_event_ticket_type(db: AsyncSession, event_ticket_type_id: int) -> None:
    event_ticket_type = await get_event_ticket_type(db, event_ticket_type_id)
    await crud.delete_event_ticket_type(db, event_ticket_type)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="EventTicketType in use"
        )
