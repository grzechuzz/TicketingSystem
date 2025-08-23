from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.allocation.models import EventSector
from app.domain.events.models import Event
from app.domain.allocation import crud
from app.domain.allocation.schemas import EventSectorCreateDTO, EventSectorBulkCreateDTO
from app.services.venue_service import get_sector


def _ensure_venue_match(event, sector):
    if event.venue_id != sector.venue_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sector does not belong to event venue")


async def get_event_sector(db: AsyncSession, event_id: int, sector_id: int) -> EventSector:
    event_sector = await crud.get_event_sector(db, event_id, sector_id)
    if not event_sector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event_sector not found")
    return event_sector


async def list_event_sectors(db: AsyncSession, event_id: int) -> list[EventSector]:
    return await crud.list_event_sectors(db, event_id)


async def create_event_sector(db: AsyncSession, schema: EventSectorCreateDTO, event: Event) -> EventSector:
    sector = await get_sector(db, schema.sector_id)
    _ensure_venue_match(event, sector)
    data = schema.model_dump(exclude_none=True)
    data['event_id'] = event.id

    if sector.is_ga:
        data['tickets_left'] = sector.base_capacity

    event_sector = await crud.create_event_sector(db, data)

    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sector already assigned to this event")
    return event_sector


async def bulk_create_event_sectors(db: AsyncSession, schema: EventSectorBulkCreateDTO, event: Event) -> None:
    data = []
    for sec in schema.sectors:
        sector = await get_sector(db, sec.sector_id)
        _ensure_venue_match(event, sector)

        d = sec.model_dump(exclude_none=True)
        if sector.is_ga:
            d['tickets_left'] = sector.base_capacity
        data.append(d)

    await crud.bulk_add_event_sectors(db, event.id, data)


async def delete_event_sector(db: AsyncSession, event_id: int, sector_id: int) -> None:
    event_sector = await get_event_sector(db, event_id, sector_id)
    await crud.delete_event_sector(db, event_sector)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event sector in use")
