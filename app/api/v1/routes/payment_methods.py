from fastapi import APIRouter, Depends, status, Response, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.auth import get_current_user_with_roles
from app.domain.users.models import User
from app.domain.payments.schemas import PaymentMethodReadDTO, PaymentMethodCreateDTO, PaymentMethodUpdateDTO
from app.services import payment_service


router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]
admin_dependency = Depends(get_current_user_with_roles("ADMIN"))


@router.get(
    "/{payment_method_id}",
    status_code=status.HTTP_200_OK,
    response_model=PaymentMethodReadDTO,
    dependencies=[admin_dependency]
)
async def get_payment_method(payment_method_id: int, db: db_dependency):
    return await payment_service.get_payment_method(db, payment_method_id)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[PaymentMethodReadDTO],
    dependencies=[admin_dependency],
)
async def list_payment_methods(db: db_dependency):
    return await payment_service.list_all_payment_methods(db)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentMethodReadDTO,
)
async def create_payment_method(
        schema: PaymentMethodCreateDTO,
        db: db_dependency,
        user: Annotated[User, admin_dependency],
        response: Response
):
    payment_method = await payment_service.create_payment_method(db, schema)
    response.headers["Location"] = f"/payment-methods/{payment_method.id}"
    return payment_method


@router.patch(
    "/{payment_method_id}",
    status_code=status.HTTP_200_OK,
    response_model=PaymentMethodReadDTO
)
async def update_payment_method(
        payment_method_id: int,
        schema: PaymentMethodUpdateDTO,
        db: db_dependency,
        user: Annotated[User, admin_dependency]
):
    return await payment_service.update_payment_method(db, payment_method_id, schema)
