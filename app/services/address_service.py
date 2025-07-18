from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.addresses import crud
from app.domain.addresses.models import Address
from app.domain.addresses.schemas import AddressCreateDTO, AddressPutDTO
from app.domain.users.models import User

async def get_address(db: AsyncSession, address_id: int) -> Address:
    address = await crud.get_by_id(db, address_id)
    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    return address

async def list_addresses(db: AsyncSession) -> list[Address]:
    return await crud.list_all(db)

async def create_address(db: AsyncSession, schema: AddressCreateDTO) -> Address:
    data = schema.model_dump(exclude_none=True)
    address = await crud.create(db, data)
    await db.commit()
    return address

async def get_authorized_address(db: AsyncSession, address_id: int, current_user: User) -> Address:
    address = await get_address(db, address_id)

    if any(r.name == "ADMIN" for r in current_user.roles):
        return address

    if any(r.name == "ORGANIZER" for r in current_user.roles):
        org_ids = {org.id for org in address.organizers}
        user_org_ids = {org.id for org in current_user.organizers}
        if not org_ids.intersection(user_org_ids):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if address.venues:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return address

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

async def update_address(db: AsyncSession, schema: AddressPutDTO, address_id: int, current_user: User) -> Address:
    address = await get_authorized_address(db, address_id, current_user)
    data = schema.model_dump(exclude_none=True)
    address = await crud.update(address, data)
    await db.commit()
    return address
