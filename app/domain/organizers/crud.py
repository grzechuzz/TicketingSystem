from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import paginate
from app.domain import Organizer


async def get_organizer_by_id(db: AsyncSession, organizer_id: int) -> Organizer | None:
    stmt = select(Organizer).where(Organizer.id == organizer_id, Organizer.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_all_organizers(
        db: AsyncSession,
        page: int,
        page_size: int,
        *,
        name: str | None = None,
        email: str | None = None,
        registration_number: str | None = None
) -> tuple[list[Organizer], int]:
    stmt = select(Organizer)
    where = []

    if name:
        where.append(Organizer.name.ilike(f"%{name}%"))
    if email:
        where.append(Organizer.email == email)
    if registration_number:
        where.append(Organizer.registration_number == registration_number)

    items, total = await paginate(
        db,
        stmt,
        page=page,
        page_size=page_size,
        where=where,
        order_by=[Organizer.id],
        scalars=True,
        count_by=Organizer.id
    )
    return items, total


async def create_organizer(db: AsyncSession, data: dict) -> Organizer:
    organizer = Organizer(**data)
    db.add(organizer)
    return organizer


async def update_organizer(organizer: Organizer, data: dict) -> Organizer:
    for key, value in data.items():
        setattr(organizer, key, value)
    return organizer


async def delete_organizer(db: AsyncSession, organizer: Organizer) -> None:
    await db.delete(organizer)
