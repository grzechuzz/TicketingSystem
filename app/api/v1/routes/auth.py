from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES
from app.domain.users.schemas import UserCreateDTO, UserReadDTO, Token
from app.services.user_service import create_user, login_user
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
    response.headers['Location'] = f"/users/me"
    return UserReadDTO.model_validate(user)


@router.post("/login", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    token = await login_user(form.username, form.password, db)
    return {"access_token": token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}

