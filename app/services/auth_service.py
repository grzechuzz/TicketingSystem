from datetime import datetime, timezone
from fastapi import HTTPException, status, Request
from sqlalchemy.exc import IntegrityError
from app.core.auditing import audit_fail, audit_ok, roles_from_user, client_ip, http_route_id
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


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    xff = request.headers.get("X-Forwarded-For")
    ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else None))
    user_agent = request.headers.get('user-agent')
    return ip, user_agent


async def create_user(model: UserCreateDTO, db: AsyncSession, request: Request) -> User:
    hashed_password = hash_password(model.password.get_secret_value())
    payload = model.model_dump(exclude_none=True, exclude={'password', 'password_confirm'})
    payload["email"] = payload["email"].strip().lower()

    user = User(**payload)
    user.password_hash = hashed_password

    role = await get_role_by_name('CUSTOMER', db)
    if not role:
        await audit_fail(
            request.app.state.redis,
            scope="AUTH",
            action="REGISTER",
            reason="Role CUSTOMER not found",
            actor_ip=client_ip(request),
            route=http_route_id(request),
            meta={"email": payload["email"]}
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Role CUSTOMER not found')

    user.roles.append(role)
    db.add(user)

    try:
        await db.flush()
    except IntegrityError as e:
        await audit_fail(
            request.app.state.redis,
            scope="AUTH",
            action="REGISTER",
            reason="Duplicate email or phone",
            actor_ip=client_ip(request),
            route=http_route_id(request),
            meta={"email": payload["email"]},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or phone number already exists!"
        ) from e
    await audit_ok(
        request.app.state.redis,
        scope="AUTH",
        action="REGISTER",
        actor_user_id=user.id,
        actor_roles=roles_from_user(user),
        actor_ip=client_ip(request),
        route=http_route_id(request),
        meta={"email": user.email},
    )

    return user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    email = email.strip().lower()
    user = await get_user_by_email(email, db)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={"WWW-Authenticate": "Bearer"}
        )
    if user.is_active is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account is inactive')
    return user


async def login_user(email: str, password: str, db: AsyncSession, request: Request) -> LoginResponse:
    try:
        user = await authenticate_user(email, password, db)
    except HTTPException as e:
        reason = e.detail
        await audit_fail(
            request.app.state.redis,
            scope="AUTH",
            action="LOGIN",
            reason=reason,
            actor_ip=client_ip(request),
            route=http_route_id(request),
            meta={"email": email.strip().lower()},
        )
        raise

    raw_refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_refresh_token, REFRESH_TOKEN_PEPPER)
    expires_at = new_expiry(REFRESH_TOKEN_TTL_DAYS)

    ip, user_agent = _client_meta(request)
    session = await create_session(db, user.id, token_hash, expires_at, ip, user_agent)
    access = create_access_token(user.id, sid=str(session.id))

    await audit_ok(
        request.app.state.redis,
        scope="AUTH",
        action="LOGIN",
        actor_user_id=user.id,
        actor_roles=roles_from_user(user),
        actor_ip=client_ip(request),
        route=http_route_id(request),
        object_type="auth_session",
        object_id=None,
        meta={"sid": str(session.id)},
    )

    return LoginResponse(
        access_token=access,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=raw_refresh_token,
        refresh_expires_in=int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        sid=str(session.id)
    )


async def refresh_tokens(db: AsyncSession, raw_refresh_token: str, request: Request) -> LoginResponse:
    now = datetime.now(timezone.utc)
    token_hash = hash_refresh_token(raw_refresh_token, REFRESH_TOKEN_PEPPER)

    session = await get_active_session_by_hash(db, token_hash)
    if not session:
        await audit_fail(
            request.app.state.redis,
            scope="AUTH",
            action="REFRESH",
            reason="Refresh not found or revoked",
            actor_ip=client_ip(request),
            route=http_route_id(request),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')

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

    await audit_ok(
        request.app.state.redis,
        scope="AUTH",
        action="REFRESH",
        actor_user_id=session.user.id,
        actor_roles=roles_from_user(session.user),
        actor_ip=client_ip(request),
        route=http_route_id(request),
        object_type="auth_session",
        object_id=None,
        meta={"sid": str(session.id), "rotated": rotated, "sliding": slid},
    )

    return LoginResponse(
        access_token=access,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh_token,
        refresh_expires_in=int((new_expires - now).total_seconds()),
        sid=str(session.id)
    )


async def logout_with_refresh(db: AsyncSession, raw_refresh_token: str, request: Request) -> None:
    token_hash = hash_refresh_token(raw_refresh_token, REFRESH_TOKEN_PEPPER)
    session = await get_active_session_by_hash(db, token_hash)
    if session:
        await revoke_session(db, session)
        await audit_ok(
            request.app.state.redis,
            scope="AUTH",
            action="LOGOUT",
            actor_user_id=session.user.id,
            actor_ip=client_ip(request),
            route=http_route_id(request),
            meta={"sid": str(session.id)}
        )


async def logout_all(db: AsyncSession, user_id: int, request: Request) -> None:
    await revoke_all_for_user(db, user_id=user_id)
    await audit_ok(
        request.app.state.redis,
        scope="AUTH",
        action="LOGOUT",
        actor_user_id=user_id,
        actor_ip=client_ip(request),
        route=http_route_id(request)
    )
