from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Address


async def get_address_by_id(db: AsyncSession, address_id: int) -> Address | None:
    stmt = select(Address).where(Address.id == address_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_all_addresses(db: AsyncSession) -> list[Address]:
    stmt = select(Address)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_address(db: AsyncSession, data: dict) -> Address:
    address = Address(**data)
    db.add(address)
    return address


async def update_address(address: Address, data: dict) -> Address:
    for k, v in data.items():
        setattr(address, k, v)
    return address
