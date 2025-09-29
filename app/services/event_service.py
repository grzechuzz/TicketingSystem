from fastapi import HTTPException, status, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.events.models import Event, EventStatus
from app.domain.events.schemas import EventCreateDTO, EventUpdateDTO, EventReadDTO, PublicEventsQueryDTO, \
    OrganizerEventsQueryDTO, AdminEventsQueryDTO
from app.domain.users.models import User
from app.core.pagination import PageDTO
from app.core.auditing import AuditSpan
from app.services.venue_service import get_venue
from app.domain.events import crud
from datetime import datetime, timezone


PUBLIC_STATUSES = {EventStatus.ON_SALE, EventStatus.PLANNED}


def _get_roles(user: User) -> set[str]:
    return {role.name for role in user.roles}


def _get_organizer_ids(user: User) -> set[int]:
    return {org.id for org in user.organizers}


def _validate_event_times_on_create(data: dict) -> None:
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


def _validate_event_times_on_update(data: dict, ev: Event) -> None:
    es = data.get("event_start", ev.event_start)
    ee = data.get("event_end",  ev.event_end)
    ss = data.get("sales_start", ev.sales_start)
    se = data.get("sales_end",  ev.sales_end)

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


async def get_event(db: AsyncSession, event_id: int, user: User) -> Event:
    event = await crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    roles = _get_roles(user)

    if "ADMIN" in roles:
        return event

    if "ORGANIZER" in roles and event.organizer_id in _get_organizer_ids(user):
        return event

    if event.status in PUBLIC_STATUSES:
        return event

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")


async def list_public_events(db: AsyncSession, query: PublicEventsQueryDTO) -> PageDTO[EventReadDTO]:
    events, total = await crud.list_events(
        db,
        page=query.page,
        page_size=query.page_size,
        statuses=PUBLIC_STATUSES,
        name=query.name,
        date_from=query.date_from,
        date_to=query.date_to
    )

    items = [EventReadDTO.model_validate(event) for event in events]

    return PageDTO(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


async def list_events_for_organizer(
        db: AsyncSession,
        user: User,
        query: OrganizerEventsQueryDTO
) -> PageDTO[EventReadDTO]:
    if "ORGANIZER" not in _get_roles(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    statuses = [query.status] if query.status is not None else None

    events, total = await crud.list_events(
        db,
        page=query.page,
        page_size=query.page_size,
        statuses=statuses,
        organizer_ids=_get_organizer_ids(user),
        name=query.name
    )

    items = [EventReadDTO.model_validate(event) for event in events]

    return PageDTO(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


async def list_events_for_admin(db: AsyncSession, query: AdminEventsQueryDTO) -> PageDTO[EventReadDTO]:
    organizer_ids = [query.organizer_id] if query.organizer_id is not None else None

    events, total = await crud.list_events(
        db,
        page=query.page,
        page_size=query.page_size,
        statuses=query.statuses,
        organizer_ids=organizer_ids,
        venue_id=query.venue_id,
        name=query.name,
        date_from=query.date_from,
        date_to=query.date_to,
    )

    items = [EventReadDTO.model_validate(e) for e in events]

    return PageDTO(items=items, total=total, page=query.page, page_size=query.page_size)


async def create_event(
        db: AsyncSession,
        organizer_id: int,
        schema: EventCreateDTO,
        user: User,
        request: Request
) -> Event:
    async with AuditSpan(
        request,
        scope="EVENTS",
        action="CREATE",
        user=user,
        object_type="event",
        organizer_id=organizer_id,
        meta={"venue_id": schema.venue_id}
    ) as span:
        await get_venue(db, schema.venue_id)
        data = schema.model_dump(exclude_none=True)
        data['organizer_id'] = organizer_id
        _validate_event_times_on_create(data)

        event = await crud.create_event(db, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event time conflict") from e

        span.object_id = event.id
        span.event_id = event.id
        return event


async def update_event(db: AsyncSession, schema: EventUpdateDTO, event: Event, user: User, request: Request) -> Event:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="EVENTS",
        action="UPDATE",
        user=user,
        object_type="event",
        organizer_id=event.organizer_id,
        event_id=event.id,
        meta={"fields": fields}
    ) as span:
        data = schema.model_dump(exclude_none=True)
        _validate_event_times_on_update(data, event)

        event = await crud.update_event(event, data)
        try:
            await db.flush()
            await db.refresh(event)
        except IntegrityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event time conflict") from e
        span.object_id = event.id
        return event


async def update_event_status(
        db: AsyncSession,
        new_status: EventStatus,
        event_id: int,
        user: User,
        request: Request
) -> Event:
    async with AuditSpan(
        request,
        scope="EVENTS",
        action="SET_STATUS",
        user=user,
        object_type="event",
        event_id=event_id
    ) as span:
        event = await crud.get_event_by_id(db, event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        span.organizer_id = event.organizer_id
        span.object_id = event.id

        allowed_transitions = {
            EventStatus.AWAITING_APPROVAL: {EventStatus.PLANNED, EventStatus.REJECTED},
            EventStatus.PLANNED: {EventStatus.ON_SALE, EventStatus.CANCELLED},
            EventStatus.ON_SALE: {EventStatus.ENDED, EventStatus.CANCELLED}
        }

        current = event.status
        if new_status == current:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is already set")

        allowed = allowed_transitions.get(current, set())
        if new_status not in allowed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid status transition")

        event.status = new_status
        try:
            await db.flush()
            await db.refresh(event)
        except IntegrityError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Statuses conflict") from e

        span.meta.update({"from": current, "to": new_status})
        return event
