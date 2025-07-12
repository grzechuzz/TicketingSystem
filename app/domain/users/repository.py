from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
from .models import Role, User

async def get_role_by_name(name: str, db: AsyncSession) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    result = await db.execute(stmt)
    return result.one_or_none()

async def email_exists(email: str, db: AsyncSession) -> bool:
    stmt = select(exists().where(User.email == email))
    return await db.scalar(stmt)

async def phone_number_exists(phone_number: str, db: AsyncSession) -> bool:
    stmt = select(exists().where(User.phone_number == phone_number))
    return await db.scalar(stmt)
