from app.core.database import Base
from enum import Enum
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Identity, Text, ForeignKey, Numeric, TIMESTAMP, func, Enum as SQLEnum, UniqueConstraint, \
    CheckConstraint, Boolean, text


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    payments: Mapped[list["Payment"]] = relationship(back_populates="payment_method", lazy="selectin")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    payment_method_id: Mapped[int] = mapped_column(ForeignKey("payment_methods.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus, name="payment_status"),
                                                  nullable=False, server_default=PaymentStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship(back_populates="payments", lazy="selectin")
    payment_method: Mapped["PaymentMethod"] = relationship(back_populates="payments", lazy="selectin")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_amount_nonneg"),
    )
