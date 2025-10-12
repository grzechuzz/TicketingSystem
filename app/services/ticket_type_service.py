from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.pricing.models import TicketType
from app.domain.pricing import crud
from app.domain.pricing.schemas import TicketTypeCreateDTO
from app.core.auditing import AuditSpan
from app.domain.exceptions import NotFound, Conflict


async def get_ticket_type(db: AsyncSession, ticket_type_id: int) -> TicketType:
    ticket_type = await crud.get_ticket_type(db, ticket_type_id)
    if not ticket_type:
        raise NotFound("Ticket type not found", ctx={"ticket_type_id": ticket_type_id})
    return ticket_type


async def list_ticket_types(db: AsyncSession) -> list[TicketType]:
    return await crud.list_ticket_types(db)


async def create_ticket_type(db: AsyncSession, schema: TicketTypeCreateDTO) -> TicketType:
    async with AuditSpan(
        scope="TICKET_TYPES",
        action="CREATE",
        object_type="ticket_type",
        meta={"name": schema.name}
    ) as span:
        data = schema.model_dump(exclude_none=True)
        ticket_type = await crud.create_ticket_type(db, data)
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("Ticket type already exists", ctx={"name": schema.name}) from e
        span.object_id = ticket_type.id
        return ticket_type


async def delete_ticket_type(db: AsyncSession, ticket_type_id: int) -> None:
    async with AuditSpan(
        scope="TICKET_TYPES",
        action="DELETE",
        object_type="ticket_type",
        object_id=ticket_type_id,
    ):
        ticket_type = await get_ticket_type(db, ticket_type_id)
        await crud.delete_ticket_type(db, ticket_type)
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("Ticket type in use", ctx={"ticket_type_id": ticket_type_id}) from e
