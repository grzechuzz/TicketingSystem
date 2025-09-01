from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domain.users.models import User
from app.domain.booking.schemas import UserOrdersQueryDTO, OrderListItemDTO, OrderDetailsDTO, TicketReadItemDTO, \
    AdminOrdersQueryDTO, AdminOrderListItemDTO, AdminOrderDetailsDTO
from app.core.pagination import PageDTO
from app.core.dependencies import get_current_user_with_roles
from app.services import orders_service

router = APIRouter(tags=["orders"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.get(
    "/users/me/orders",
    response_model=PageDTO[OrderListItemDTO],
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK
)
async def list_user_orders(
        db: db_dependency,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER"))],
        query: Annotated[UserOrdersQueryDTO, Depends()]
):
    return await orders_service.list_user_orders(db, user, query)


@router.get(
    "/users/me/orders/{order_id}",
    response_model=OrderDetailsDTO,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK
)
async def get_user_order(
        db: db_dependency,
        order_id: int,
        user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER"))]
):
    return await orders_service.get_user_order(db, user, order_id)


@router.get(
    "/admin/orders",
    response_model=PageDTO[AdminOrderListItemDTO],
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def list_orders_admin(db: db_dependency, query: Annotated[AdminOrdersQueryDTO, Depends()]):
    return await orders_service.list_orders_admin(db, query)


@router.get(
    "/admin/orders/{order_id}",
    response_model=AdminOrderDetailsDTO,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def get_order_admin(db: db_dependency, order_id: int):
    return await orders_service.get_order_admin(db, order_id)
