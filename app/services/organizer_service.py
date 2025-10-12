from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import PageDTO
from app.domain.organizers.models import Organizer
from app.domain.organizers import crud
from app.domain.organizers.schemas import OrganizerCreateDTO, OrganizerPutDTO, OrganizerReadDTO, OrganizersQueryDTO
from app.core.auditing import AuditSpan
from app.domain.exceptions import NotFound, Conflict


async def get_organizer(db: AsyncSession, organizer_id: int) -> Organizer:
    organizer = await crud.get_organizer_by_id(db, organizer_id)
    if not organizer:
        raise NotFound("Organizer not found", ctx={"organizer_id": organizer_id})
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
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        scope="ORGANIZERS",
        action="CREATE",
        object_type="organizer",
        meta={"fields": fields}
    ) as span:
        data = schema.model_dump(exclude_none=True)
        organizer = await crud.create_organizer(db, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("Organizer already exists", ctx={"fields": fields}) from e
        span.object_id = organizer.id
        return organizer


async def update_organizer(
        db: AsyncSession,
        schema: OrganizerPutDTO,
        organizer_id: int
) -> Organizer:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        scope="ORGANIZERS",
        action="UPDATE",
        object_type="organizer",
        object_id=organizer_id,
        meta={"fields": fields}
    ):
        organizer = await get_organizer(db, organizer_id)
        data = schema.model_dump(exclude_none=True)
        organizer = await crud.update_organizer(organizer, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("Organizer update violates unique constraint", ctx={"fields": fields}) from e
        return organizer


async def delete_organizer(db: AsyncSession, organizer_id: int) -> None:
    async with AuditSpan(
        scope="ORGANIZERS",
        action="DELETE",
        object_type="organizer",
        object_id=organizer_id
    ):
        organizer = await get_organizer(db, organizer_id)
        await crud.delete_organizer(db, organizer)
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("Organizer in use", ctx={"organizer_id": organizer_id}) from e
