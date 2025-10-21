from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies.auth import get_current_user_with_roles
from app.core.pagination import PageDTO
from app.domain.users.models import User
from app.domain.users.schemas import UserReadDTO, AdminUsersQueryDTO, PasswordChangeDTO, AdminUserListItemDTO, \
    UserRolesUpdateDTO
from app.services import users_service

router = APIRouter(tags=["users"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]
me_dependency = Annotated[User, Depends(get_current_user_with_roles("CUSTOMER", "ORGANIZER", "ADMIN"))]


@router.get(
    "/users/me",
    status_code=status.HTTP_200_OK,
    response_model=UserReadDTO,
    response_model_exclude_none=True
)
async def get_me(user: me_dependency):
    return user


@router.post(
    "/users/me/password",
    status_code=status.HTTP_204_NO_CONTENT
)
async def change_my_password(schema: PasswordChangeDTO, db: db_dependency, user: me_dependency):
    await users_service.change_password(db, user, schema)


@router.get(
    "/admin/users",
    status_code=status.HTTP_200_OK,
    response_model=PageDTO[AdminUserListItemDTO],
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def list_admin_users(db: db_dependency, query: Annotated[AdminUsersQueryDTO, Depends()]):
    return await users_service.list_users_admin(db, query)


@router.patch(
    "/admin/users/{user_id}/roles",
    status_code=status.HTTP_200_OK,
    response_model=AdminUserListItemDTO,
    dependencies=[Depends(get_current_user_with_roles("ADMIN"))]
)
async def set_user_roles(user_id: int, schema: UserRolesUpdateDTO, db: db_dependency):
    return await users_service.update_user_roles(db, user_id, schema)
