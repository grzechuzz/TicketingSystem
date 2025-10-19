from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.core.auditing import AuditSpan
from app.domain.auth.crud import create_session, get_active_session_by_hash, touch_session, revoke_session, \
    revoke_all_for_user
from app.domain.auth.schemas import LoginResponse
from app.domain.users.schemas import UserCreateDTO
from app.domain.users.models import User
from app.domain.users.crud import get_role_by_name, get_user_by_email
from app.core.security import hash_password, verify_password, create_access_token, generate_refresh_token, \
    hash_refresh_token, new_expiry
from app.core.config import REFRESH_TOKEN_PEPPER, REFRESH_TOKEN_TTL_DAYS, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_ROTATE, \
    REFRESH_SLIDING
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.exceptions import InternalError, Conflict, Unauthorized, Forbidden
from anyio import to_thread


async def create_user(model: UserCreateDTO, db: AsyncSession) -> User:
    payload = model.model_dump(exclude_none=True, exclude={'password', 'password_confirm'})
    payload["email"] = payload["email"].strip().lower()

    async with AuditSpan(scope="AUTH", action="REGISTER", object_type="user") as span:
        hashed_password = await to_thread.run_sync(hash_password, model.password.get_secret_value())
        user = User(**payload)
        user.password_hash = hashed_password

        role = await get_role_by_name('CUSTOMER', db)
        if not role:
            raise InternalError("Role CUSTOMER not found")

        user.roles.append(role)
        db.add(user)
        try:
            await db.flush()
        except IntegrityError as e:
            raise Conflict("User already exists", ctx={"email": payload["email"]}) from e

        span.object_id = user.id
        return user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    user = await get_user_by_email(email.strip().lower(), db)
    ok = False
    if user:
        ok = await to_thread.run_sync(verify_password, password, user.password_hash)
    if not user or not ok:
        raise Unauthorized("Incorrect email or password", ctx={"reason": "bad_credentials"})
    if not user.is_active:
        raise Forbidden("Account is inactive", ctx={"reason": "inactive"})
    return user


async def login_user(
        email: str,
        password: str,
        db: AsyncSession,
        *,
        ip: str | None = None,
        user_agent: str | None = None
) -> LoginResponse:
    async with AuditSpan(scope="AUTH", action="LOGIN", object_type="auth_session") as span:
        user = await authenticate_user(email, password, db)

        raw_refresh_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_refresh_token, REFRESH_TOKEN_PEPPER)
        expires_at = new_expiry(REFRESH_TOKEN_TTL_DAYS)
        session = await create_session(db, user.id, token_hash, expires_at, ip, user_agent)
        access = create_access_token(subject=user.id, sid=str(session.id))

        span.object_id = session.id
        span.meta.update({"sid": str(session.id)})

        return LoginResponse(
            access_token=access,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=raw_refresh_token,
            refresh_expires_in=int((expires_at - datetime.now(timezone.utc)).total_seconds()),
            sid=str(session.id)
        )


async def refresh_tokens(db: AsyncSession, raw_refresh_token: str) -> LoginResponse:
    async with AuditSpan(scope="AUTH", action="REFRESH", object_type="auth_session") as span:
        now = datetime.now(timezone.utc)
        token_hash = hash_refresh_token(raw_refresh_token, REFRESH_TOKEN_PEPPER)

        session = await get_active_session_by_hash(db, token_hash)
        if not session:
            raise Unauthorized('Invalid refresh token', ctx={"reason": "invalid_token"})

        span.meta.update({"sid": str(session.id)})

        rotated = False
        slid = False

        new_refresh_token = raw_refresh_token
        new_expires = session.expires_at
        if REFRESH_ROTATE:
            rotated = True
            new_refresh_token = generate_refresh_token()
            new_hash = hash_refresh_token(new_refresh_token, REFRESH_TOKEN_PEPPER)
            new_expires = new_expiry(REFRESH_TOKEN_TTL_DAYS) if REFRESH_SLIDING else session.expires_at
            slid = REFRESH_SLIDING
            await touch_session(db, session, new_hash, new_expires)
        else:
            if REFRESH_SLIDING:
                new_expires = new_expiry(REFRESH_TOKEN_TTL_DAYS)
                slid = True
                await touch_session(db, session=session, new_expires_at=new_expires)
            else:
                await touch_session(db, session=session)

        access = create_access_token(subject=session.user.id, sid=str(session.id))

        span.object_id = session.id
        span.meta.update({"rotated": rotated, "sliding": slid})

        return LoginResponse(
            access_token=access,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=new_refresh_token,
            refresh_expires_in=int((new_expires - now).total_seconds()),
            sid=str(session.id)
        )


async def logout_with_refresh(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token, REFRESH_TOKEN_PEPPER)
    session = await get_active_session_by_hash(db, token_hash)
    if not session:
        return

    async with AuditSpan(
        scope="AUTH",
        action="LOGOUT",
        object_type="auth_session",
        object_id=session.id,
        meta={"sid": str(session.id)}
    ):
        await revoke_session(db, session)


async def logout_all(db: AsyncSession, user: User) -> None:
    async with AuditSpan(
            scope="AUTH",
            action="LOGOUT",
            object_type="auth_session",
            meta={"all_sessions": True}
    ):
        await revoke_all_for_user(db, user_id=user.id)
