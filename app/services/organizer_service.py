from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageDTO
from app.domain import Organizer
from app.domain.organizers import crud
from app.domain.organizers.schemas import OrganizerCreateDTO, OrganizerPutDTO, OrganizerReadDTO, OrganizersQueryDTO
from app.domain.users.models import User


async def get_organizer(db: AsyncSession, organizer_id: int) -> Organizer:
    organizer = await crud.get_organizer_by_id(db, organizer_id)
    if not organizer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organizer not found")
    return organizer


async def list_organizers(db: AsyncSession, query: OrganizersQueryDTO) -> PageDTO[OrganizerReadDTO]:
    organizers, total = await crud.list_all_organizers(
        db,
        query.page,
        query.page_size,
        name=query.name,
        email=query.email,
        registration_number=query.registration_number
    )

    items = [OrganizerReadDTO.model_validate(organizer) for organizer in organizers]

    return PageDTO(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


async def create_organizer(db: AsyncSession, schema: OrganizerCreateDTO) -> Organizer:
    data = schema.model_dump(exclude_none=True)
    organizer = await crud.create_organizer(db, data)
    await db.flush()
    return organizer


async def get_authorized_organizer(db: AsyncSession, organizer_id: int, current_user: User) -> Organizer:
    organizer = await get_organizer(db, organizer_id)

    if any(r.name == "ADMIN" for r in current_user.roles):
        return organizer

    if any(r.name == "ORGANIZER" for r in current_user.roles):
        if any(u.id == current_user.id for u in organizer.users):
            return organizer

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def update_organizer(
        db: AsyncSession,
        schema: OrganizerPutDTO,
        organizer_id: int,
        current_user: User
) -> Organizer:
    organizer = await get_authorized_organizer(db, organizer_id, current_user)
    data = schema.model_dump(exclude_none=True)
    organizer = await crud.update_organizer(organizer, data)
    return organizer


async def delete_organizer(db: AsyncSession, organizer_id: int) -> None:
    organizer = await get_organizer(db, organizer_id)
    await crud.delete_organizer(db, organizer)
