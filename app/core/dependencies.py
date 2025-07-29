from fastapi import Depends, HTTPException, status, Path
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.core.config import SECRET_KEY
from app.domain.users.models import User
from app.domain.users.schemas import TokenPayload

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_token_payload(token: Annotated[str, Depends(oauth2_bearer)]) -> TokenPayload:
    try:
        raw_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
        if not set(payload.roles).intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission Denied")

        stmt = select(User).where(User.id == int(payload.sub), User.is_active.is_(True))
        result = await db.execute(stmt)
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user
    return _inner


def pick_valid_organizer_id(organizer_id: Annotated[int | None, Path(default=None)] = None):
    async def _inner(user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]) -> int:
        if any(r.name == "ADMIN" for r in user.roles):
            if organizer_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="organizer_id is required for admin"
                )
            return organizer_id

        user_orgs = {o.id for o in user.organizers}
        if not user_orgs:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not linked to any organizer")

        if organizer_id is None:
            if len(user_orgs) == 1:
                return next(iter(user_orgs))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="organizer_id is required, organizer linked to multiple organizers"
            )

        if organizer_id not in user_orgs:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for this organizer")

        return organizer_id
    return Depends(_inner)
