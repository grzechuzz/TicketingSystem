from fastapi import APIRouter, Depends, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.payments.schemas import PaymentMethodReadDTO
from app.domain.users.models import User
from app.services import booking_service, payment_service
from app.domain.booking.schemas import OrderDetailsDTO, TicketHolderReadDTO, TicketHolderUpsertDTO, InvoiceRequestDTO, \
    InvoiceReadDTO, InvoiceUpsertDTO

router = APIRouter(prefix="/users/me/cart", tags=["cart"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]
user_dependency = Annotated[User, Depends(get_current_user_with_roles("CUSTOMER"))]

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=OrderDetailsDTO,
    response_model_exclude_none=True
)
async def get_cart(db: db_dependency, user: user_dependency):
    order = await booking_service.get_user_pending_order(db, user)
    return order


@router.delete(
    "/items/{ticket_instance_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_item(ticket_instance_id: int, db: db_dependency, user: user_dependency):
    await booking_service.remove_ticket_instance(db, user, ticket_instance_id)


@router.put(
    "/items/{ticket_instance_id}/holder",
    status_code=status.HTTP_200_OK,
    response_model=TicketHolderReadDTO,
    response_model_exclude_none=True
)
async def upsert_ticket_holder(
        ticket_instance_id: int,
        db: db_dependency,
        schema: TicketHolderUpsertDTO,
        user: user_dependency
):
    ticket_holder = await booking_service.upsert_ticket_holder(db, ticket_instance_id, schema, user)
    return ticket_holder


@router.patch(
    "/invoice-request",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def set_invoice_requested(db: db_dependency, schema: InvoiceRequestDTO, user: user_dependency):
    await booking_service.set_invoice_requested(db, schema, user)


@router.put(
    "/invoice",
    status_code=status.HTTP_200_OK,
    response_model=InvoiceReadDTO,
    response_model_exclude_none=True
)
async def upsert_invoice(db: db_dependency, schema: InvoiceUpsertDTO, user: user_dependency):
    invoice = await booking_service.upsert_invoice(db, schema, user)
    return invoice


@router.post(
    "/checkout",
    status_code=status.HTTP_200_OK,
    response_model=OrderDetailsDTO,
    response_model_exclude_none=True
)
async def checkout(db: db_dependency, user: user_dependency):
    order = await booking_service.checkout(db, user)
    return order


@router.post(
    "/reopen",
    status_code=status.HTTP_200_OK,
    response_model=OrderDetailsDTO,
    response_model_exclude_none=True
)
async def reopen_cart(db: db_dependency, user: user_dependency):
    order = await booking_service.reopen_cart(db, user)
    return order


@router.get(
    "/payment-methods",
    status_code=status.HTTP_200_OK,
    response_model=list[PaymentMethodReadDTO]
)
async def list_active_payment_methods(db: db_dependency, user: user_dependency):
    return await payment_service.list_active_payment_methods(db)
