import asyncio
from anyio import to_thread
from app.core.security import hash_password
from app.domain.users.crud import get_role_by_name, get_user_by_email
from app.domain.users.models import User
from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD
from app.core.database import AsyncSessionLocal


async def seed_admin_user(db) -> User | None:
    if not ADMIN_PASSWORD or not ADMIN_EMAIL:
        print("Missing password or email - skipping seed...")
        return None

    admin_role = await get_role_by_name("ADMIN", db)
    organizer_role = await get_role_by_name("ORGANIZER", db)
    customer_role = await get_role_by_name("CUSTOMER", db)

    user = await get_user_by_email(ADMIN_EMAIL, db)

    if not user:
        user = User(
            first_name="Admin",
            last_name="Admin",
            email=ADMIN_EMAIL,
            password_hash=await to_thread.run_sync(hash_password, ADMIN_PASSWORD)
        )
        db.add(user)
        have = set()
    else:
        have = {r.name for r in user.roles}

    need = [r for r in (admin_role, organizer_role, customer_role) if r and r.name not in have]
    if need:
        user.roles.extend(need)

    await db.flush()
    return user


async def main():
    async with AsyncSessionLocal() as db:
        user = await seed_admin_user(db)
        await db.commit()
        if user:
            print(f"Admin OK: {user.email}")


if __name__ == "__main__":
    asyncio.run(main())
