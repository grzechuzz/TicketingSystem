from fastapi import APIRouter, status, Depends, HTTPException, Response
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import pick_valid_organizer_id, get_current_user_with_roles
from app.domain.events.schemas import EventCreateDTO, EventReadDTO, EventUpdateDTO
from app.services import event_service
from app.domain.users.models import User

router = APIRouter(tags=["events"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/organizers/{organizer_id}/events",
    status_code=status.HTTP_201_CREATED,
    response_model=EventReadDTO,
    response_model_exclude_none=True,
    name="create_event",
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]   # optional, for readability
)
async def create_event(
        organizer_id: Annotated[int, pick_valid_organizer_id],
        schema: EventCreateDTO,
        db: db_dependency,
        response: Response
):
    event = await event_service.create_event(db, organizer_id, schema)
    response.headers["Location"] = f"/events/{event.id}"
    return event


@router.get(
    "/events",
    status_code=status.HTTP_200_OK,
    response_model=list[EventReadDTO]
)
async def list_events(db: db_dependency):
    return await event_service.list_events(db)


@router.get(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventReadDTO
)
async def get_event(event_id: int, db: db_dependency):
    event = await event_service.get_event(db, event_id)
    return event


@router.patch(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]  # optional, for readability
)
async def patch_event(
        event_id: int,
        schema: EventUpdateDTO,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]
):
    event = await event_service.get_event(db, event_id)

    if not any(r.name == "ADMIN" for r in user.roles):
        if event.organizer_id not in {o.id for o in user.organizers}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")

    updated = await event_service.update_event(db, schema, venue_id)
    return updated
