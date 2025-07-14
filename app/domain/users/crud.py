from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
from .models import Role, User

async def get_role_by_name(name: str, db: AsyncSession) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    result = await db.execute(stmt)
    return result.one_or_none()
