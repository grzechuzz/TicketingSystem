from app.core.database import Base
from enum import Enum
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Identity, text, Text, ForeignKey, Numeric, TIMESTAMP, func, Enum as SQLEnum, UniqueConstraint, \
    CheckConstraint, Boolean, Date, Index, String


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TicketStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REFUNDED = "REFUNDED"
    EXPIRED = "EXPIRED"


class InvoiceType(str, Enum):
    PERSON = "PERSON"
    COMPANY = "COMPANY"


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
    invoice: Mapped["Invoice"] = relationship(back_populates="order", lazy="selectin", uselist=False)

    __table_args__ = (
        CheckConstraint("total_price >= 0", name="chk_total_price_nonneg"),
        Index(
            "uq_orders_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'AWAITING_PAYMENT')")
        ),
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
    price_net_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vat_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    price_gross_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ticket_type_name_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="ticket_instances", lazy="selectin")
    seat: Mapped["Seat"] = relationship(back_populates="ticket_instances", lazy="selectin")
    ticket_holder: Mapped["TicketHolder"] = relationship(back_populates="ticket_instance", lazy="selectin", uselist=False)
    ticket: Mapped["Ticket"] = relationship(back_populates="ticket_instance", lazy="selectin", uselist=False)
    event: Mapped["Event"] = relationship(back_populates="ticket_instances", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("event_id", "seat_id", name="uq_event_seat"),
        CheckConstraint("price_net_snapshot >= 0", name="chk_price_net_nonneg"),
        CheckConstraint("price_gross_snapshot >= 0", name="chk_price_gross_nonneg"),
        CheckConstraint("vat_rate_snapshot >= 1.00", name="chk_vat_rate")
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


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    ticket_instance_id: Mapped[int] = mapped_column(ForeignKey("ticket_instances.id", ondelete="RESTRICT"),
                                                    nullable=False, unique=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[TicketStatus] = mapped_column(SQLEnum(TicketStatus, name="ticket_status"),
                                                 nullable=False, server_default=TicketStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    ticket_instance: Mapped["TicketInstance"] = relationship(back_populates="ticket", lazy="selectin", uselist=False)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    invoice_number: Mapped[str | None] = mapped_column(Text, unique=True, index=True, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, server_default="PLN")
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True
    )
    invoice_type: Mapped[InvoiceType] = mapped_column(SQLEnum(InvoiceType, name="invoice_type"), nullable=False)
    # PERSON: full_name, COMPANY: company_name + tax_id
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    street: Mapped[str] = mapped_column(Text, nullable=False)
    postal_code: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship(back_populates="invoice", lazy="selectin", uselist=False)
