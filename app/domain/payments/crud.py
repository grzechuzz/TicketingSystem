from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import PaymentMethod


async def get_payment_method(db: AsyncSession, payment_method_id: int) -> PaymentMethod | None:
    result = await db.execute(select(PaymentMethod).where(PaymentMethod.id == payment_method_id))
    return result.scalars().first()


async def list_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    result = await db.execute(select(PaymentMethod).order_by(PaymentMethod.id))
    return result.scalars().all()


async def list_active_payment_methods(db: AsyncSession) -> list[PaymentMethod]:
    result = await db.execute(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.id))
    return result.scalars().all()


async def create_payment_method(db: AsyncSession, data: dict) -> PaymentMethod:
    payment_method = PaymentMethod(**data)
    db.add(payment_method)
    return payment_method


async def update_payment_method(payment_method: PaymentMethod, data: dict) -> PaymentMethod:
    for key, value in data.items():
        setattr(payment_method, key, value)
    return payment_method
