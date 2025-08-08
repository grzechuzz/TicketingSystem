from app.core.database import Base
from enum import Enum
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Identity, text, Text, ForeignKey, Numeric, TIMESTAMP, func, Enum as SQLEnum, UniqueConstraint, \
    CheckConstraint, Boolean, Date


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    payments: Mapped[list["Payment"]] = relationship(back_populates="payment_method", lazy="selectin")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    reserved_until: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, index=True)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus, name="order_status"),
                                                nullable=False, server_default=OrderStatus.PENDING.value)
    invoice_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="orders", lazy="selectin")
    ticket_instances: Mapped[list["TicketInstance"]] = relationship(back_populates="order", lazy="selectin")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", lazy="selectin")

    __table_args__ = (
        CheckConstraint("total_price >= 0", name="chk_total_price_nonneg"),
    )


class TicketInstance(Base):
    __tablename__ = "ticket_instances"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    event_ticket_type_id: Mapped[int] = mapped_column(ForeignKey("event_ticket_types.id"), nullable=False, index=True)
    seat_id: Mapped[int | None] = mapped_column(ForeignKey("seats.id"), nullable=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    reserved_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(),
                                                  nullable=False)

    order: Mapped["Order"] = relationship(back_populates="ticket_instances", lazy="selectin")
    seat: Mapped["Seat"] = relationship(back_populates="ticket_instances", lazy="selectin")
    ticket_holder: Mapped["TicketHolder"] = relationship(back_populates="ticket_instance", lazy="selectin", uselist=False)

    __table_args__ = (
        UniqueConstraint("event_id", "seat_id", name="uq_event_seat"),
    )


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


class TicketHolder(Base):
    __tablename__ = "ticket_holders"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    ticket_instance_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_instances.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    identification_number: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    ticket_instance: Mapped["TicketInstance"] = relationship(back_populates="ticket_holder", lazy="selectin")

    __table_args__ = (
        CheckConstraint("birth_date <= CURRENT_DATE", name="chk_holder_birth_not_future"),
    )
