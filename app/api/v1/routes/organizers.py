from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.organizers.schemas import OrganizerCreateDTO, OrganizerReadDTO, OrganizerPutDTO
from app.domain.users.models import User
from app.core.dependencies import get_db, get_current_user_with_roles
from app.services.organizer_service import (
    create_organizer,
    list_organizers,
    get_organizer,
    update_organizer,
    delete_organizer
)
from typing import Annotated

router = APIRouter(prefix="/organizers", tags=["organizers"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrganizerReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def create(db: db_dependency, schema: OrganizerCreateDTO, response: Response):
    organizer = await create_organizer(db, schema)
    response.headers["Location"] = f"{router.prefix}/{organizer.id}"
    return organizer

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[OrganizerReadDTO],
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get_all(db: db_dependency):
    organizers = await list_organizers(db)
    return organizers

@router.get(
    "/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN", "ORGANIZER", "CUSTOMER"))]
)
async def get(db: db_dependency, organizer_id: int):
    organizer = await get_organizer(db, organizer_id)
    return organizer

@router.put(
    "/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerReadDTO,
    response_model_exclude_none=True
)
async def update(
        schema: OrganizerPutDTO,
        organizer_id: int,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]
):
    organizer = await update_organizer(db, schema, organizer_id, user)
    return organizer

@router.delete(
    "/{organizer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def delete(organizer_id: int, db: db_dependency):
    return await delete_organizer(db, organizer_id)
