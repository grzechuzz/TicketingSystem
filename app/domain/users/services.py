from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from .schemas import UserCreateDTO
from .models import User
from .repository import get_role_by_name, email_exists, phone_number_exists
from app.core.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession

async def create_user(model: UserCreateDTO, db: AsyncSession) -> User:
    if await email_exists(model.email, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists!")

    if model.phone_number and await phone_number_exists(model.phone_number, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this phone number already exists!")

    hashed_password = hash_password(model.password)

    user = User(**model.model_dump(exclude_none=True, exclude={'password'}))
    user.password_hash = hashed_password

    role = await get_role_by_name('CUSTOMER', db)
    if not role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Role CUSTOMER not found')

    user.roles.append(role)

    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or phone number already exists!"
        )

    return user
