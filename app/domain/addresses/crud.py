from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Address


async def get_address_by_id(db: AsyncSession, address_id: int) -> Address | None:
    stmt = select(Address).where(Address.id == address_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_all_addresses(db: AsyncSession, page: int, page_size: int) -> tuple[list[Address], int]:
    total = await db.scalar(select(func.count()).select_from(Address))
    stmt = select(Address).order_by(Address.id).limit(page_size).offset((page - 1) * page_size)
    result = await db.scalars(stmt)
    return list(result), int(total or 0)


async def create_address(db: AsyncSession, data: dict) -> Address:
    address = Address(**data)
    db.add(address)
    return address


async def update_address(address: Address, data: dict) -> Address:
    for k, v in data.items():
        setattr(address, k, v)
    return address
