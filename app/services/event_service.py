from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.events.models import Event
from app.domain.events.schemas import EventCreateDTO, EventUpdateDTO
from app.services.venue_service import get_venue
from app.domain.events import crud
from datetime import datetime, timezone


def validate_event_times_on_create(data: dict) -> None:
    es = data["event_start"]
    ee = data["event_end"]
    ss = data["sales_start"]
    se = data["sales_end"]

    if ee <= es:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="event_end must be after event_start"
        )
    if se <= ss:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sales_end must be after sales_start"
        )


def validate_event_times_on_update(data: dict, ev: Event) -> None:
    es = data.get("event_start", ev.event_start)
    ee = data.get("event_end",   ev.event_end)
    ss = data.get("sales_start", ev.sales_start)
    se = data.get("sales_end",   ev.sales_end)

    if ee <= es:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="event_end must be after event_start"
        )
    if se <= ss:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sales_end must be after sales_start"
        )

    now = datetime.now(timezone.utc)
    if "sales_start" in data and ev.sales_start <= now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot change sales_start after sales began"
        )
    if "event_start" in data and ev.event_start <= now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot change event_start after event started"
        )


async def get_event(db: AsyncSession, event_id: int) -> Event:
    event = await crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


async def list_events(db: AsyncSession) -> list[Event]:
    return await crud.list_all_events(db)


async def create_event(db: AsyncSession, organizer_id: int, schema: EventCreateDTO) -> Event:
    await get_venue(db, schema.venue_id)
    data = schema.model_dump(exclude_none=True)
    data['organizer_id'] = organizer_id
    validate_event_times_on_create(data)
    event = await crud.create_event(db, data)
    await db.commit()
    return event


async def update_event(db: AsyncSession, schema: EventUpdateDTO, event_id: int) -> Event:
    event = await get_event(db, event_id)
    data = schema.model_dump(exclude_none=True)
    validate_event_times_on_update(data, event)
    event = await crud.update_event(event, data)
    await db.commit()
    return event

