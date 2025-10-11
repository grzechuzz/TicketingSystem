from typing import Annotated
from fastapi import Depends
from app.core.database import get_db
from app.domain.users.models import User
from app.domain.addresses.models import Address
from app.domain.addresses import crud
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies.auth import get_current_user_with_roles
from app.domain.exceptions import Forbidden, NotFound

async def require_authorized_address(
        address_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: User = Depends(get_current_user_with_roles("ADMIN", "ORGANIZER")),
) -> Address:
    address = await crud.get_address_by_id(db, address_id)
    if not address:
        raise NotFound("Address not found", ctx={"address_id": address_id})

    roles = {r.name for r in user.roles}

    if "ADMIN" in roles:
        return address

    org_ids = {org.id for org in address.organizers}
    user_org_ids = {org.id for org in user.organizers}
    if not org_ids.intersection(user_org_ids):
        raise Forbidden("Access denied", ctx={"address_id": address_id, "reason": "organizer_mismatch"})

    if address.venue:
        raise Forbidden("Access denied", ctx={"address_id": address_id, "reason": "address_attached_to_venue"})

    return address
