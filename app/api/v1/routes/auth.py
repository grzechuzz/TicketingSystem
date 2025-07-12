from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domain.users.schemas import UserCreateDTO, UserReadDTO
from app.domain.users.services import create_user
from typing import Annotated

router = APIRouter(prefix='/auth', tags=['auth'])

db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.post(
    '/register',
    status_code=status.HTTP_201_CREATED,
    response_model=UserReadDTO,
    response_model_exclude_none=True
)
async def register(db: db_dependency, model: UserCreateDTO, response: Response):
    user = await create_user(model, db)
    response.headers['Location'] = f"api/v1/users/{user.id}"
    return UserReadDTO.model_validate(user)
