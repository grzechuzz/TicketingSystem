from fastapi import APIRouter, Depends, status, Response
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.payments.schemas import PaymentMethodReadDTO, PaymentMethodCreateDTO, PaymentMethodUpdateDTO
from app.services import payment_service

router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]
admin_dependency = Depends(get_current_user_with_roles("ADMIN"))


@router.get(
    "/{payment_method_id}",
    status_code=status.HTTP_200_OK,
    response_model=PaymentMethodReadDTO,
    dependencies=[admin_dependency],
)
async def get_method(db: db_dependency, payment_method_id: int):
    return await payment_service.get_payment_method(db, payment_method_id)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[PaymentMethodReadDTO],
    dependencies=[admin_dependency],
)
async def list_methods(db: db_dependency):
    return await payment_service.list_all_payment_methods(db)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentMethodReadDTO,
    dependencies=[admin_dependency],
)
async def create_method(db: db_dependency, schema: PaymentMethodCreateDTO, response: Response):
    payment_method = await payment_service.create_payment_method(db, schema)
    response.headers["Location"] = f"/payment-methods/{payment_method.id}"
    return payment_method


@router.patch(
    "/{payment_method_id}",
    status_code=status.HTTP_200_OK,
    response_model=PaymentMethodReadDTO,
    dependencies=[admin_dependency]
)
async def update_method(db: db_dependency, payment_method_id: int, schema: PaymentMethodUpdateDTO):
    return await payment_service.update_payment_method(db, payment_method_id, schema)
