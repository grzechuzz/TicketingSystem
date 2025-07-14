from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import SECURITY_KEY, ALGORITHM
from app.domain.users.models import User
from app.domain.users.schemas import TokenPayload

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/login")
db_dependency = Annotated[AsyncSession, Depends(get_db)]

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)], db: db_dependency) -> User:
    try:
        raw_payload = jwt.decode(token, SECURITY_KEY, algorithms=[ALGORITHM])
        payload = TokenPayload.model_validate(raw_payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == int(payload.sub))
    result = await db.execute(stmt)
    user = result.scalars().one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
