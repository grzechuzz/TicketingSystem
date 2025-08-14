from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.domain.users.schemas import UserCreateDTO
from app.domain.users.models import User
from app.domain.users.crud import get_role_by_name, get_user_by_email
from app.core.security import hash_password, verify_password, create_access_token
from sqlalchemy.ext.asyncio import AsyncSession

async def create_user(model: UserCreateDTO, db: AsyncSession) -> User:
    hashed_password = hash_password(model.password)

    user = User(**model.model_dump(exclude_none=True, exclude={'password'}))
    user.password_hash = hashed_password

    role = await get_role_by_name('CUSTOMER', db)
    if not role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Role CUSTOMER not found')

    user.roles.append(role)

    db.add(user)

    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or phone number already exists!"
        ) from e

    return user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    user = await get_user_by_email(email, db)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

async def login_user(email: str, password: str, db: AsyncSession) -> str:
    user = await authenticate_user(email, password, db)
    roles = [r.name for r in user.roles]
    return create_access_token(subject=user.id, roles=roles)
