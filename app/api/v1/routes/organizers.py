from fastapi import APIRouter, status, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.organizers.schemas import OrganizerCreateDTO, OrganizerReadDTO, OrganizerPutDTO, OrganizersQueryDTO
from app.domain.users.models import User
from app.core.dependencies.auth import get_current_user_with_roles
from app.core.dependencies.events import require_organizer_member
from app.core.database import get_db
from app.core.pagination import PageDTO
from app.services import organizer_service
from typing import Annotated


router = APIRouter(prefix="/organizers", tags=["organizers"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrganizerReadDTO,
    response_model_exclude_none=True
)
async def create_organizer(
        schema: OrganizerCreateDTO,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN"))],
        response: Response,
        request: Request
):
    organizer = await organizer_service.create_organizer(db, schema, user, request)
    response.headers["Location"] = f"{router.prefix}/{organizer.id}"
    return organizer


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[OrganizerReadDTO],
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def list_organizers(db: db_dependency, query: Annotated[OrganizersQueryDTO, Depends()]):
    organizers = await organizer_service.list_organizers(db, query)
    return organizers


@router.get(
    "/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_organizer(organizer_id: int, db: db_dependency):
    organizer = await organizer_service.get_organizer(db, organizer_id)
    return organizer


@router.put(
    "/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerReadDTO,
    response_model_exclude_none=True
)
async def update_organizer(
        organizer_id: Annotated[int, Depends(require_organizer_member)],
        schema: OrganizerPutDTO,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))],
        request: Request
):
    organizer = await organizer_service.update_organizer(db, schema, organizer_id, user, request)
    return organizer


@router.delete("/{organizer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organizer(
        organizer_id: int,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN"))],
        request: Request
):
    return await organizer_service.delete_organizer(db, organizer_id, user, request)
