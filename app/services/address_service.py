from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auditing import AuditSpan
from app.core.pagination import PageDTO
from app.domain.addresses import crud
from app.domain.addresses.models import Address
from app.domain.addresses.schemas import AddressCreateDTO, AddressPutDTO, AddressesQueryDTO, AddressReadDTO
from app.domain.exceptions import NotFound


async def get_address(db: AsyncSession, address_id: int) -> Address:
    address = await crud.get_address_by_id(db, address_id)
    if not address:
        raise NotFound("Address not found", ctx={"address_id": address_id})
    return address


async def list_addresses(db: AsyncSession, query: AddressesQueryDTO) -> PageDTO[AddressReadDTO]:
    addresses, total = await crud.list_all_addresses(db, query.page, query.page_size)
    items = [AddressReadDTO.model_validate(address) for address in addresses]
    return PageDTO[AddressReadDTO](
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size
    )


async def create_address(db: AsyncSession, schema: AddressCreateDTO) -> Address:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        scope="ADDRESSES",
        action="CREATE",
        object_type="address",
        meta={"fields": fields}
    ) as span:
        data = schema.model_dump(exclude_none=True)
        address = await crud.create_address(db, data)
        await db.flush()
        span.object_id = address.id
        return address


async def update_address(
        db: AsyncSession,
        schema: AddressPutDTO,
        address: Address
) -> Address:
    fields = list(schema.model_dump(exclude_none=True).keys())
    async with AuditSpan(
        scope="ADDRESSES",
        action="UPDATE",
        object_type="address",
        meta={"fields": fields}
    ) as span:
        span.object_id = address.id
        data = schema.model_dump(exclude_none=True)
        address = await crud.update_address(address, data)
        await db.flush()
        return address
