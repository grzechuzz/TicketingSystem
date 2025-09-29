from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.core.config import SECRET_KEY, JWT_ISSUER, JWT_AUDIENCE
from app.domain.users.models import User
from app.domain.auth.schemas import TokenPayload


oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_token_payload(token: Annotated[str, Depends(oauth2_bearer)]) -> TokenPayload:
    try:
        raw_payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"verify_aud": True, "leeway": 5}
        )
        if raw_payload.get("typ") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return TokenPayload.model_validate(raw_payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_with_roles(*allowed_roles: str):
    async def _inner(payload: Annotated[TokenPayload, Depends(get_token_payload)],
                     db: Annotated[AsyncSession, Depends(get_db)]) -> User:
        stmt = select(User).where(User.id == int(payload.sub), User.is_active.is_(True))

        result = await db.execute(stmt)
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if allowed_roles and not any(r.name in allowed_roles for r in user.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user
    return _inner
