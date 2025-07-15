from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Address

async def create_address(data: dict, db: AsyncSession) -> Address:
    address = Address(**data)
    db.add(address)
    await db.commit()
    return address

async def get_address(id: int, db: AsyncSession) -> Address | None:
    result = await db.execute(select(Address).where(Address.id == id))
    return result.one_or_none()
