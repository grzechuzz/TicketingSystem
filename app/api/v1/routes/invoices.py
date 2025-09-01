from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.users.models import User
from app.domain.booking.schemas import UserInvoicesQueryDTO, InvoiceListItemDTO, InvoiceDetailsDTO, \
    AdminInvoiceListItemDTO, AdminInvoicesQueryDTO
from app.core.pagination import PageDTO
from app.services import invoices_service


router = APIRouter(tags=["invoices"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/users/me/invoices",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[InvoiceListItemDTO],
    response_model_exclude_none=True
)
async def list_user_invoices(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER"))],
        query: Annotated[UserInvoicesQueryDTO, Depends()]
):
    return await invoices_service.list_user_invoices(db, user, query)


@router.get(
    "/users/me/invoices/{invoice_id}",
    status_code=status.HTTP_200_OK,
    response_model=InvoiceDetailsDTO,
    response_model_exclude_none=True
)
async def get_user_invoice(
        invoice_id: int,
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER"))],
):
    return await invoices_service.get_user_invoice_details(db, user, invoice_id)


@router.get(
    "/admin/invoices",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[AdminInvoiceListItemDTO],
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def list_invoices_admin(db: db_dependency, query: Annotated[AdminInvoicesQueryDTO, Depends()]):
    return await invoices_service.list_admin_invoices(db, query)


@router.get(
    "/admin/invoices/{invoice_id}",
    status_code=status.HTTP_200_OK,
    response_model=InvoiceDetailsDTO,
    response_model_exclude_none=True,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def get_invoice_admin(
        invoice_id: int,
        db: db_dependency
):
    return await invoices_service.get_invoice_details_admin(db, invoice_id)
