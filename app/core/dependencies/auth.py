from fastapi import Depends
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
from app.domain.exceptions import Unauthorized, Forbidden
from app.core.ctx import AUTH_ROLES_CTX, AUTH_USER_ID_CTX


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
            raise Unauthorized("Invalid token type", ctx={"reason": "invalid_type"})
        return TokenPayload.model_validate(raw_payload)
    except (JWTError, ValidationError):
        raise Unauthorized("Invalid authentication credentials", ctx={"reason": "invalid_token"})


def get_current_user_with_roles(*allowed_roles: str):
    allowed = set(allowed_roles)

    async def _inner(payload: Annotated[TokenPayload, Depends(get_token_payload)],
                     db: Annotated[AsyncSession, Depends(get_db)]) -> User:
        stmt = select(User).where(User.id == int(payload.sub), User.is_active.is_(True))
        result = await db.execute(stmt)
        user = result.scalars().first()
        if not user:
            raise Unauthorized("User not found", ctx={"user_id": payload.sub})

        roles = {r.name for r in user.roles}
        AUTH_ROLES_CTX.set(roles)
        AUTH_USER_ID_CTX.set(user.id)

        if allowed and roles.isdisjoint(allowed):
            raise Forbidden("Permission denied", ctx={"required": list(allowed_roles), "user_roles": list(roles)})
        return user
    return _inner
