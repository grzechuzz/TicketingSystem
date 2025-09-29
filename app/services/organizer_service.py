from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import PageDTO
from app.domain.organizers.models import Organizer
from app.domain.organizers import crud
from app.domain.organizers.schemas import OrganizerCreateDTO, OrganizerPutDTO, OrganizerReadDTO, OrganizersQueryDTO
from app.domain.users.models import User
from app.core.auditing import AuditSpan


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


async def create_organizer(db: AsyncSession, schema: OrganizerCreateDTO, user: User, request: Request) -> Organizer:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="ORGANIZERS",
        action="CREATE",
        user=user,
        object_type="organizer",
        meta={"fields": fields}
    ) as span:
        data = schema.model_dump(exclude_none=True)
        organizer = await crud.create_organizer(db, data)
        await db.flush()
        span.object_id = organizer.id
        return organizer


async def update_organizer(
        db: AsyncSession,
        schema: OrganizerPutDTO,
        organizer_id: int,
        current_user: User,
        request: Request
) -> Organizer:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        request,
        scope="ORGANIZERS",
        action="UPDATE",
        user=current_user,
        object_type="organizer",
        object_id=organizer_id,
        meta={"fields": fields}
    ):
        organizer = await get_organizer(db, organizer_id)
        data = schema.model_dump(exclude_none=True)
        organizer = await crud.update_organizer(organizer, data)
        await db.flush()
        return organizer


async def delete_organizer(db: AsyncSession, organizer_id: int, user: User, request: Request) -> None:
    async with AuditSpan(
        request,
        scope="ORGANIZERS",
        action="DELETE",
        user=user,
        object_type="organizer",
        object_id=organizer_id
    ):
        organizer = await get_organizer(db, organizer_id)
        await crud.delete_organizer(db, organizer)
