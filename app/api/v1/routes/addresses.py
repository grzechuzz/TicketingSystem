from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.addresses.models import Address
from app.domain.addresses.schemas import AddressCreateDTO, AddressReadDTO
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
async def create_address(model: AddressCreateDTO, db: db_dependency):
    address = Address(**model.model_dump(exclude_none=True))
    db.add(address)
    await db.commit()
    return AddressReadDTO.model_validate(address)

