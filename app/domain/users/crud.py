from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from .models import Role, User


async def get_role_by_name(name: str, db: AsyncSession) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    stmt = select(User).options(selectinload(User.roles)).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalars().first()
