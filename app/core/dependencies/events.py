from fastapi import Depends, HTTPException, status
from typing import Annotated, NamedTuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.auth import get_current_user_with_roles
from app.domain.users.models import User
from app.domain.events.models import Event
from app.domain.pricing.models import EventTicketType
from app.domain.allocation.models import EventSector

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if any(r.name == "ADMIN" for r in user.roles):
        return event

    if event.organizer_id not in {o.id for o in user.organizers}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    return event


def require_organizer_member(
        organizer_id: int,
        user: Annotated[User, Depends(ADMIN_OR_ORG)]
) -> int:
    if any(r.name == "ADMIN" for r in user.roles):
        return organizer_id

    if organizer_id not in {o.id for o in user.organizers}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

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
    stmt = await db.execute(
        select(EventTicketType, EventSector.event_id)
        .join(EventSector)
        .where(EventTicketType.id == event_ticket_type_id)
    )
    row = (await db.execute(stmt).tuples().first())
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event ticket type not found")

    event_ticket_type, event_id = row
    await _ensure_event_owner(event_id, db=db, user=user)
    return EventTicketTypeActor(event_ticket_type, user)
