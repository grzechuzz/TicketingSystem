from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain import Organizer

async def get_by_id(db: AsyncSession, organizer_id: int) -> Organizer | None:
    stmt = select(Organizer).where(Organizer.id == organizer_id, Organizer.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalars().first()

async def list_all(db: AsyncSession) -> list[Organizer]:
    stmt = select(Organizer)
    result = await db.execute(stmt)
    return result.scalars().all()

async def create(db: AsyncSession, data: dict) -> Organizer:
    organizer = Organizer(**data)
    db.add(organizer)
    return organizer

async def update(organizer: Organizer, data: dict) -> Organizer:
    for key, value in data.items():
        setattr(organizer, key, value)
    return organizer

async def delete(db: AsyncSession, organizer: Organizer) -> None:
    await db.delete(organizer)

