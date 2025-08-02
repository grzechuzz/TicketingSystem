from fastapi import APIRouter, status, Depends, Response, Query
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_organizer_member, require_event_owner, get_current_user_with_roles
from app.domain.events.schemas import EventCreateDTO, EventReadDTO, EventUpdateDTO, EventStatusDTO
from app.domain.users.models import User
from app.services import event_service
from app.domain.events.models import Event, EventStatus

router = APIRouter(tags=["events"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.get(
    "/events",
    status_code=status.HTTP_200_OK,
    response_model=list[EventReadDTO],
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def list_events(db: db_dependency):
    return await event_service.list_public_events(db)


@router.get(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventReadDTO
)
async def get_event(
        event_id: int,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]

):
    return await event_service.get_event(db, event_id, user)


@router.get(
    "/organizers/me/events",
    status_code=status.HTTP_200_OK,
    response_model=list[EventReadDTO],
)
async def list_organizer_events(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ORGANIZER"))]):
    return await event_service.list_events_for_organizer(db, user)


@router.post(
    "/organizers/{organizer_id:int}/events",
    status_code=status.HTTP_201_CREATED,
    response_model=EventReadDTO,
    response_model_exclude_none=True
)
async def create_event(
        organizer_id: Annotated[int, Depends(require_organizer_member)],
        schema: EventCreateDTO,
        db: db_dependency,
        response: Response
):
    event = await event_service.create_event(db, organizer_id, schema)
    response.headers["Location"] = f"/events/{event.id}"
    return event


@router.get(
    "/admin/events",
    status_code=status.HTTP_200_OK,
    response_model=list[EventReadDTO],
)
async def list_admin_events(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN"))],
        statuses: Annotated[list[EventStatus] | None, Query()] = None
):
    return await event_service.list_events_for_admin(db, statuses)


@router.patch(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventReadDTO,
    response_model_exclude_none=True
)
async def patch_event(
        event: Annotated[Event, Depends(require_event_owner)],
        schema: EventUpdateDTO,
        db: db_dependency
):
    event = await event_service.update_event(db, schema, event)
    return event


@router.patch(
    "/events/{event_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=EventReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def patch_event_status(event_id: int, schema: EventStatusDTO, db: db_dependency):
    event = await event_service.update_event_status(db, schema.new_status, event_id)
    return event
