from fastapi import APIRouter, status, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.users.models import User
from app.core.database import get_db
from app.core.pagination import PageDTO
from app.core.dependencies.auth import get_current_user_with_roles
from app.services import address_service
from app.domain.addresses.schemas import AddressCreateDTO, AddressReadDTO, AddressPutDTO, AddressesQueryDTO
from typing import Annotated


router = APIRouter(prefix='/addresses', tags=['addresses'])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AddressReadDTO,
    response_model_exclude_none=True
)
async def create_address(
        schema: AddressCreateDTO,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER'))],
        response: Response,
        request: Request
):
    address = await address_service.create_address(db, schema, user, request)
    response.headers["Location"] = f"{router.prefix}/{address.id}"
    return address


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[AddressReadDTO],
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def list_addresses(db: db_dependency, query: Annotated[AddressesQueryDTO, Depends()]):
    addresses = await address_service.list_addresses(db, query)
    return addresses


@router.get(
    "/{address_id}",
    status_code=status.HTTP_200_OK,
    response_model=AddressReadDTO,
    dependencies=[Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER', 'CUSTOMER'))]
)
async def get_address(address_id: int, db: db_dependency):
    address = await address_service.get_address(db, address_id)
    return address


@router.put(
    "/{address_id}",
    status_code=status.HTTP_200_OK,
    response_model=AddressReadDTO
)
async def update_address(
        address_id: int,
        schema: AddressPutDTO,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles('ADMIN', 'ORGANIZER'))],
        request: Request
):
    address = await address_service.update_address(db, schema, address_id, user, request)
    return address
