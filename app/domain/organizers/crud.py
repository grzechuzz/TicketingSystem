from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain import Organizer


async def get_organizer_by_id(db: AsyncSession, organizer_id: int) -> Organizer | None:
    stmt = select(Organizer).where(Organizer.id == organizer_id, Organizer.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_all_organizers(db: AsyncSession, page: int, page_size: int) -> tuple[list[Organizer], int]:
    total = await db.scalar(select(func.count()).select_from(Organizer))
    stmt = select(Organizer).order_by(Organizer.id).limit(page_size).offset((page - 1) * page_size)
    result = await db.scalars(stmt)
    return list(result), int(total or 0)


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
