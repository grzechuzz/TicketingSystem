from fastapi import HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.pricing import crud
from app.domain.pricing.schemas import EventTicketTypeCreateDTO, EventTicketTypeUpdateDTO, \
    EventTicketTypeBulkCreateDTO
from app.domain.pricing.models import EventTicketType
from app.domain.allocation.models import EventSector
from app.domain.users.models import User
from app.core.auditing import AuditSpan


async def _event_id_for_ett(db: AsyncSession, ett: EventTicketType) -> int | None:
    return await db.scalar(select(EventSector.event_id).where(EventSector.id == ett.event_sector_id))


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
        event_sector: EventSector,
        user: User,
        request: Request
) -> EventTicketType:
    data = schema.model_dump(exclude_none=True)
    data["event_sector_id"] = event_sector.id

    meta = {
        "event_sector_id": event_sector.id,
        "sector_id": getattr(event_sector, "sector_id", None),
    }

    async with AuditSpan(
        request,
        scope="EVENT_TICKET_TYPES",
        action="CREATE",
        user=user,
        object_type="event_ticket_type",
        event_id=event_sector.event_id,
        meta=meta
    ) as span:
        event_ticket_type = await crud.create_event_ticket_type(db, data)
        try:
            await db.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This ticket type already defined for this sector"
            )
        span.object_id = event_ticket_type.id
        return event_ticket_type


async def bulk_create_event_ticket_types(
        db: AsyncSession,
        schema: EventTicketTypeBulkCreateDTO,
        event_sector: EventSector,
        user: User,
        request: Request
) -> None:
    data = [ett.model_dump(exclude_none=True) for ett in schema.event_ticket_types]
    meta = {
        "event_sector_id": event_sector.id,
        "count": len(data)
    }

    async with AuditSpan(
        request,
        scope="EVENT_TICKET_TYPES",
        action="CREATE_BULK",
        user=user,
        object_type="event_ticket_type",
        event_id=event_sector.event_id,
        meta=meta
    ):
        await crud.bulk_add_event_ticket_types(db, event_sector.id, data)


async def update_event_ticket_type(
        db: AsyncSession,
        event_ticket_type: EventTicketType,
        schema: EventTicketTypeUpdateDTO,
        user: User,
        request: Request
) -> EventTicketType:
    fields = list(schema.model_dump(exclude_none=True).keys())
    event_id = await _event_id_for_ett(db, event_ticket_type)

    async with AuditSpan(
            request,
            scope="EVENT_TICKET_TYPES",
            action="UPDATE",
            user=user,
            object_type="event_ticket_type",
            event_id=event_id,
            meta={"fields": fields, "event_sector_id": event_ticket_type.event_sector_id}
    ) as span:
        data = schema.model_dump(exclude_none=True)
        event_ticket_type = await crud.update_event_ticket_type(event_ticket_type, data)
        try:
            await db.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This ticket type already defined for this sector"
            )
        span.object_id = event_ticket_type.id
        return event_ticket_type


async def delete_event_ticket_type(
        db: AsyncSession,
        event_ticket_type: EventTicketType,
        user: User,
        request: Request
) -> None:
    event_id = await _event_id_for_ett(db, event_ticket_type)
    async with AuditSpan(
        request,
        scope="EVENT_TICKET_TYPES",
        action="DELETE",
        user=user,
        object_type="event_ticket_type",
        event_id=event_id,
        meta={"event_sector_id": event_ticket_type.event_sector_id}
    ) as span:
        crud.delete_event_ticket_type(db, event_ticket_type)
        try:
            await db.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="EventTicketType in use"
            )
        span.object_id = event_ticket_type.id
