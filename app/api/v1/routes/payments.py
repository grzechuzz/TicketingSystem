from fastapi import APIRouter, Depends, status, Response, Header
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.auth import get_current_user_with_roles
from app.domain.users.models import User
from app.domain.payments.schemas import PaymentCreateDTO, PaymentReadDTO, PaymentFinalizeDTO
from app.services import payment_service


router = APIRouter(prefix="/users/me/cart/payments", tags=["payments"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]
user_dependency = Annotated[User, Depends(get_current_user_with_roles("CUSTOMER"))]


@router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentReadDTO,
    response_model_exclude_none=True,
)
async def start_payment(
        schema: PaymentCreateDTO,
        db: db_dependency,
        user: user_dependency,
        response: Response,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
):
    payment, redirect_url = await payment_service.start_payment(db, user, schema, idempotency_key)
    response.headers["Location"] = f"{router.prefix}/{payment.id}"
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "payment_method_id": payment.payment_method_id,
        "amount": payment.amount,
        "provider": payment.provider,
        "status": payment.status,
        "created_at": payment.created_at,
        "paid_at": payment.paid_at,
        "redirect_url": redirect_url,
    }


@router.post(
    "/{payment_id}/finalize",
    status_code=status.HTTP_200_OK,
    response_model=PaymentReadDTO,
    response_model_exclude_none=True,
)
async def finalize_payment(
        payment_id: int,
        schema: PaymentFinalizeDTO,
        db: db_dependency,
        user: user_dependency,
):
    payment = await payment_service.finalize_payment(db, user, payment_id, schema.success)
    return payment


@router.get(
    "/{payment_id}",
    status_code=status.HTTP_200_OK,
    response_model=PaymentReadDTO,
    response_model_exclude_none=True,
)
async def get_payment(payment_id: int, db: db_dependency, user: user_dependency):
    return await payment_service.get_payment_for_user(db, payment_id, user)
