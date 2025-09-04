from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.users.models import User
from app.domain.users.schemas import UserReadDTO


router = APIRouter(prefix="/users", tags=["users"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]
me_dependency = Annotated[User, Depends(get_current_user_with_roles("CUSTOMER", "ORGANIZER", "ADMIN"))]


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserReadDTO,
    response_model_exclude_none=True
)
async def get_me(user: me_dependency):
    return user
