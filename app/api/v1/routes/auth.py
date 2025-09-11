from fastapi import APIRouter, Depends, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_with_roles
from app.domain.users.schemas import UserCreateDTO, UserReadDTO
from app.domain.auth.schemas import LoginResponse, RefreshRequest, LogoutRequest
from app.domain.users.models import User
from app.services.auth_service import create_user, login_user, refresh_tokens, logout_all, logout_with_refresh
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


@router.post("/login", response_model=LoginResponse)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency, request: Request):
    return await login_user(form.username, form.password, db, request)


@router.post("/refresh", response_model=LoginResponse)
async def refresh(schema: RefreshRequest, db: db_dependency, request: Request):
    return await refresh_tokens(db, schema.refresh_token, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(schema: LogoutRequest, db: db_dependency):
    await logout_with_refresh(db, schema.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_sessions(
    db: db_dependency,
    user: Annotated[User, Depends(get_current_user_with_roles("CUSTOMER", "ORGANIZER", "ADMIN"))],
):
    await logout_all(db, user.id)
