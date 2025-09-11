from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.auth.models import AuthRefreshSession


async def create_session(
        db: AsyncSession,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None
) -> AuthRefreshSession:
    now = datetime.now(timezone.utc)
    session = AuthRefreshSession(
        user_id=user_id,
        token_hash=token_hash,
        created_at=now,
        last_used_at=now,
        expires_at=expires_at,
        ip=ip,
        user_agent=user_agent
    )
    db.add(session)
    await db.flush()
    return session


async def get_active_session_by_hash(db: AsyncSession, token_hash: str) -> AuthRefreshSession | None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(AuthRefreshSession)
        .where(
            AuthRefreshSession.token_hash == token_hash,
            AuthRefreshSession.expires_at > now,
            AuthRefreshSession.revoked_at.is_(None)
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def touch_session(
        db: AsyncSession,
        session: AuthRefreshSession,
        new_token_hash: str | None = None,
        new_expires_at: datetime | None = None
) -> AuthRefreshSession:
    values = {"last_used_at": datetime.now(timezone.utc)}
    if new_token_hash is not None:
        values["token_hash"] = new_token_hash
    if new_expires_at is not None:
        values["expires_at"] = new_expires_at

    await db.execute(
        update(AuthRefreshSession)
        .where(AuthRefreshSession.id == session.id)
        .values(**values)
    )


async def revoke_session(db: AsyncSession, session: AuthRefreshSession) -> None:
    await db.execute(
        update(AuthRefreshSession)
        .where(AuthRefreshSession.id == session.id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.flush()


async def revoke_all_for_user(db: AsyncSession, *, user_id: int) -> None:
    await db.execute(
        update(AuthRefreshSession)
        .where(
            AuthRefreshSession.user_id == user_id,
            AuthRefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.flush()
