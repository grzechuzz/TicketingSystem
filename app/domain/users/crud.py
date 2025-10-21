from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, or_
from app.core.pagination import paginate
from .models import Role, User


async def get_role_by_name(name: str, db: AsyncSession) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    stmt = select(User).options(selectinload(User.roles)).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_id(user_id: int, db: AsyncSession) -> User | None:
    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_roles_by_names(names: list[str], db: AsyncSession) -> list[Role]:
    if not names:
        return []
    stmt = select(Role).where(Role.name.in_(names))
    return list((await db.execute(stmt)).scalars().all())


async def list_all_users(
    db: AsyncSession,
    page: int,
    page_size: int,
    *,
    email: str | None = None,
    name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    created_from=None,
    created_to=None,
) -> tuple[list[User], int]:
    stmt = select(User).options(selectinload(User.roles))
    where = []

    if email:
        where.append(func.lower(User.email) == func.lower(email))
    if name:
        like = f"%{name}%"
        where.append(or_(User.first_name.ilike(like), User.last_name.ilike(like)))
    if role:
        where.append(User.roles.any(Role.name == role))
    if is_active is not None:
        where.append(User.is_active.is_(is_active))
    if created_from is not None:
        where.append(User.created_at >= created_from)
    if created_to is not None:
        where.append(User.created_at <= created_to)

    items, total = await paginate(
        db,
        base_stmt=stmt,
        page=page,
        page_size=page_size,
        where=where,
        order_by=[User.created_at.desc(), User.id],
        scalars=True,
        count_by=User.id,
    )
    return items, total
