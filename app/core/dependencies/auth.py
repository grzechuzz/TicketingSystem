from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, NamedTuple
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.core.config import SECRET_KEY, JWT_ISSUER, JWT_AUDIENCE
from app.domain.users.models import User
from app.domain.auth.schemas import TokenPayload
from app.domain.events.models import Event
from app.domain.pricing.models import EventTicketType
from app.domain.allocation.models import EventSector

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/login")


class EventActor(NamedTuple):
    event: Event
    user: User


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


def require_organizer_member(
        organizer_id: int,
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]
) -> int:
    if any(r.name == "ADMIN" for r in user.roles):
        return organizer_id

    if organizer_id not in {o.id for o in user.organizers}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    return organizer_id


async def require_event_owner(
        event_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]
) -> Event:
    stmt = select(Event).where(Event.id == event_id)
    result = await db.execute(stmt)
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if any(r.name == "ADMIN" for r in user.roles):
        return event

    if event.organizer_id not in {o.id for o in user.organizers}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    return event


async def require_event_ticket_type_access(
        event_ticket_type_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[User, Depends(get_current_user_with_roles("ADMIN", "ORGANIZER"))]
) -> EventTicketType:
    stmt = select(EventTicketType).join(EventSector).where(EventTicketType.id == event_ticket_type_id)
    result = await db.execute(stmt)
    event_ticket_type = result.scalars().first()
    if not event_ticket_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event ticket type not found")

    await require_event_owner(event_ticket_type.event_sector.event_id, db=db, user=user)

    return event_ticket_type
