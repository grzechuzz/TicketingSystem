from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.users.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.services.address_service import create_address, list_addresses, get_address, update_address
from app.domain.addresses.schemas import AddressCreateDTO, AddressReadDTO, AddressPutDTO
from typing import Annotated

router = APIRouter(prefix='/addresses', tags=['addresses'])

db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AddressReadDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER'))]
)
async def create(model: AddressCreateDTO, db: db_dependency, response: Response):
    address = await create_address(db, model)
    response.headers["Location"] = f"{router.prefix}/{address.id}"
    return address

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[AddressReadDTO],
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def get_all(db: db_dependency):
    addresses = await list_addresses(db)
    return addresses

@router.get(
    "/{address_id}",
    status_code=status.HTTP_200_OK,
    response_model=AddressReadDTO,
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def get(address_id: int, db: db_dependency):
    address = await get_address(db, address_id)
    return address

@router.put(
    "/{address_id}",
    status_code=status.HTTP_200_OK,
    response_model=AddressReadDTO
)
async def update(
        model: AddressPutDTO,
        address_id: int,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER'))]
):
    address = await update_address(db, model, address_id, user)
    return address
