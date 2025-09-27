from fastapi import APIRouter, status, Depends, Response, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.events import require_event_actor, EventActor, require_organizer_member, require_event_owner
from app.core.dependencies.auth import get_current_user_with_roles
from app.core.pagination import PageDTO
from app.domain.events.schemas import EventCreateDTO, EventReadDTO, EventUpdateDTO, EventStatusDTO, AdminEventsQueryDTO, \
    PublicEventsQueryDTO, OrganizerEventsQueryDTO
from app.domain.pricing.schemas import EventTicketTypeBulkCreateDTO, EventTicketTypeCreateDTO, EventTicketTypeReadDTO
from app.domain.allocation.schemas import EventSectorReadDTO, EventSectorCreateDTO, EventSectorBulkCreateDTO
from app.domain.users.models import User
from app.services import event_service, event_sectors_service, event_ticket_type_service
from app.domain.events.models import Event


router = APIRouter(tags=["events"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/events",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[EventReadDTO],
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def list_events(db: db_dependency, query: Annotated[PublicEventsQueryDTO, Depends()]):
    return await event_service.list_public_events(db, query)


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
    response_model=PageDTO[EventReadDTO]
)
async def list_organizer_events(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ORGANIZER"))],
        query: Annotated[OrganizerEventsQueryDTO, Depends()]
):
    return await event_service.list_events_for_organizer(db, user, query)


@router.post(
    "/organizers/{organizer_id}/events",
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
    response_model=PageDTO[EventReadDTO]
)
async def list_admin_events(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN"))],
        query: Annotated[AdminEventsQueryDTO, Depends()]
):
    return await event_service.list_events_for_admin(db, query)


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


@router.get(
    "/events/{event_id}/sectors/{sector_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventSectorReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_event_sector(event_id: int, sector_id: int, db: db_dependency):
    return await event_sectors_service.get_event_sector(db, event_id, sector_id)


@router.get(
    "/events/{event_id}/sectors",
    status_code=status.HTTP_200_OK,
    response_model=list[EventSectorReadDTO],
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_all_event_sectors_by_event(event_id: int, db: db_dependency):
    return await event_sectors_service.list_event_sectors(db, event_id)


@router.post(
    "/events/{event_id}/sectors",
    status_code=status.HTTP_201_CREATED,
    response_model=EventSectorReadDTO,
    response_model_exclude_none=True
)
async def create_event_sector_for_event(
        event_actor: Annotated[EventActor, Depends(require_event_actor)],
        schema: EventSectorCreateDTO,
        db: db_dependency,
        response: Response,
        request: Request
):
    event = event_actor.event
    user = event_actor.user
    event_sector = await event_sectors_service.create_event_sector(db, schema, event, user, request)
    response.headers["Location"] = f"/events/{event.id}/sectors/{event_sector.sector_id}"
    return event_sector


@router.post(
    "/events/{event_id}/sectors/bulk",
    status_code=status.HTTP_204_NO_CONTENT
)
async def bulk_add_event_sectors_for_event(
        event_actor: Annotated[EventActor, Depends(require_event_actor)],
        schema: EventSectorBulkCreateDTO,
        db: db_dependency,
        request: Request
):
    event = event_actor.event
    user = event_actor.user
    await event_sectors_service.bulk_create_event_sectors(db, schema, event, user, request)


@router.delete(
    "/events/{event_id}/sectors/{sector_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_event_sector_for_event(
        event_actor: Annotated[EventActor, Depends(require_event_actor)],
        sector_id: int,
        db: db_dependency,
        request: Request
):
    event = event_actor.event
    user = event_actor.user
    await event_sectors_service.delete_event_sector(db, event.id, sector_id, user, request)


@router.get(
    "/events/{event_id}/sectors/{sector_id}/ticket-types",
    response_model=list[EventTicketTypeReadDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def list_ticket_types_for_event_sector(event_id: int, sector_id: int, db: db_dependency):
    event_sector = await event_sectors_service.get_event_sector(db, event_id, sector_id)
    return await event_ticket_type_service.list_event_sector_ticket_types(db, event_sector.id)


@router.post(
    "/events/{event_id}/sectors/{sector_id}/ticket-types",
    status_code=status.HTTP_201_CREATED,
    response_model=EventTicketTypeReadDTO,
    response_model_exclude_none=True
)
async def create_event_ticket_type_for_event_sector(
        event: Annotated[Event, Depends(require_event_owner)],
        sector_id: int,
        schema: EventTicketTypeCreateDTO,
        db: db_dependency,
        response: Response
):
    event_sector = await event_sectors_service.get_event_sector(db, event.id, sector_id)
    event_ticket_type = await event_ticket_type_service.create_event_ticket_type(db, schema, event_sector)
    response.headers["Location"] = f"/event-ticket-types/{event_ticket_type.id}"
    return event_ticket_type


@router.post(
    "/events/{event_id}/sectors/{sector_id}/ticket-types/bulk",
    status_code=status.HTTP_204_NO_CONTENT
)
async def bulk_add_event_ticket_types_for_event_sector(
    event: Annotated[Event, Depends(require_event_owner)],
    sector_id: int,
    schema: EventTicketTypeBulkCreateDTO,
    db: db_dependency
):
    event_sector = await event_sectors_service.get_event_sector(db, event.id, sector_id)
    await event_ticket_type_service.bulk_create_event_ticket_types(db, schema, event_sector)
