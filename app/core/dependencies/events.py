from fastapi import Depends, HTTPException, status
from typing import Annotated, NamedTuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.auth import get_current_user_with_roles
from app.domain.users.models import User
from app.domain.events.models import Event
from app.domain.pricing.models import EventTicketType
from app.domain.allocation.models import EventSector
from app.domain.exceptions import NotFound, Forbidden

ADMIN_OR_ORG = get_current_user_with_roles('ADMIN', 'ORGANIZER')


class EventActor(NamedTuple):
    event: Event
    user: User


class EventTicketTypeActor(NamedTuple):
    event_ticket_type: EventTicketType
    user: User


async def _ensure_event_owner(event_id: int, db: AsyncSession, user: User) -> Event:
    event = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    if not event:
        raise NotFound("Event not found", ctx={"event_id": event_id})

    if any(r.name == "ADMIN" for r in user.roles):
        return event

    if event.organizer_id not in {o.id for o in user.organizers}:
        raise Forbidden("Not allowed", ctx={"event_id": event_id, "reason": "organizer_mismatch"})

    return event


def require_organizer_member(
        organizer_id: int,
        user: Annotated[User, Depends(ADMIN_OR_ORG)]
) -> int:
    roles = {r.name for r in user.roles}
    if "ADMIN" in roles:
        return organizer_id

    if organizer_id not in {o.id for o in user.organizers}:
        raise Forbidden("Not allowed", ctx={"organizer_id": organizer_id, "reason": "organizer_mismatch"})

    return organizer_id


async def require_event_owner(
        event_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[User, Depends(ADMIN_OR_ORG)]
) -> Event:
    return await _ensure_event_owner(event_id, db, user)


async def require_event_actor(
        event_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[User, Depends(ADMIN_OR_ORG)]
) -> EventActor:
    event = await _ensure_event_owner(event_id, db, user)
    return EventActor(event, user)


async def require_event_ticket_type_access(
        event_ticket_type_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[User, Depends(ADMIN_OR_ORG)]
) -> EventTicketTypeActor:
    stmt = (
        select(EventTicketType, EventSector.event_id)
        .join(EventSector)
        .where(EventTicketType.id == event_ticket_type_id)
    )
    result = await db.execute(stmt)
    row = result.tuples().first()

    if not row:
        raise NotFound()

    event_ticket_type, event_id = row
    await _ensure_event_owner(event_id, db=db, user=user)
    return EventTicketTypeActor(event_ticket_type, user)
