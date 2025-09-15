from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auditing import audit_ok, audit_fail, roles_from_user, http_route_id, client_ip
from app.core.pagination import PageDTO
from app.domain.addresses import crud
from app.domain.addresses.models import Address
from app.domain.addresses.schemas import AddressCreateDTO, AddressPutDTO, AddressesQueryDTO, AddressReadDTO
from app.domain.users.models import User


async def get_address(db: AsyncSession, address_id: int) -> Address:
    address = await crud.get_address_by_id(db, address_id)
    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
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


async def create_address(db: AsyncSession, schema: AddressCreateDTO, current_user: User, request: Request) -> Address:
    data = schema.model_dump(exclude_none=True)
    address = await crud.create_address(db, data)
    await db.flush()
    await audit_ok(
        request.app.state.redis,
        scope="ADDRESSES",
        action="CREATE",
        actor_user_id=current_user.id,
        actor_roles=roles_from_user(current_user),
        actor_ip=client_ip(request),
        route=http_route_id(request),
        object_type="address",
        object_id=address.id,
        meta={"fields": list(data.keys())}
    )
    return address


async def get_authorized_address(db: AsyncSession, address_id: int, current_user: User, request: Request) -> Address:
    address = await get_address(db, address_id)

    if any(r.name == "ADMIN" for r in current_user.roles):
        return address

    if any(r.name == "ORGANIZER" for r in current_user.roles):
        org_ids = {org.id for org in address.organizers}
        user_org_ids = {org.id for org in current_user.organizers}
        if not org_ids.intersection(user_org_ids):
            await audit_fail(
                request.app.state.redis,
                scope="ADDRESSES",
                action="UPDATE",
                reason="Access denied",
                actor_user_id=current_user.id,
                actor_roles=roles_from_user(current_user),
                actor_ip=client_ip(request),
                route=http_route_id(request),
                object_type="address",
                object_id=address.id,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if address.venue:
            await audit_fail(
                request.app.state.redis,
                scope="ADDRESSES",
                action="UPDATE",
                reason="Access denied (address attached to venue)",
                actor_user_id=current_user.id,
                actor_roles=roles_from_user(current_user),
                actor_ip=client_ip(request),
                route=http_route_id(request),
                object_type="address",
                object_id=address.id,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return address

    await audit_fail(
        request.app.state.redis,
        scope="ADDRESSES",
        action="UPDATE",
        reason="Access denied (role)",
        actor_user_id=current_user.id,
        actor_roles=roles_from_user(current_user),
        actor_ip=client_ip(request),
        route=http_route_id(request),
        object_type="address",
        object_id=address.id,
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def update_address(
        db: AsyncSession,
        schema: AddressPutDTO,
        address_id: int,
        current_user: User,
        request: Request
) -> Address:
    address = await get_authorized_address(db, address_id, current_user, request)
    data = schema.model_dump(exclude_none=True)
    address = await crud.update_address(address, data)
    await db.flush()

    await audit_ok(
        request.app.state.redis,
        scope="ADDRESSES",
        action="UPDATE",
        actor_user_id=current_user.id,
        actor_roles=roles_from_user(current_user),
        actor_ip=client_ip(request),
        route=http_route_id(request),
        object_type="address",
        object_id=address.id,
        meta={"fields": list(data.keys())}
    )
    return address
