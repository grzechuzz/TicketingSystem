from app.core.database import Base
from sqlalchemy import Identity, ForeignKey, CheckConstraint, UniqueConstraint, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal


class TicketType(Base):
    __tablename__ = 'ticket_types'

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    event_ticket_types: Mapped[list['EventTicketType']] = relationship(back_populates="ticket_type", lazy="selectin")


class EventTicketType(Base):
    __tablename__ = 'event_ticket_types'

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    event_sector_id: Mapped[int] = mapped_column(ForeignKey("event_sectors.id"), nullable=False, index=True)
    ticket_type_id: Mapped[int] = mapped_column(ForeignKey("ticket_types.id"), nullable=False, index=True)
    price_net: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)

    event_sector = relationship("EventSector", back_populates="event_ticket_types", lazy="selectin")
    ticket_type = relationship("TicketType", back_populates="event_ticket_types", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("event_sector_id", "ticket_type_id", name="uq_event_sector_ticket_type"),
        CheckConstraint("price_net >= 0", name="chk_ticket_price")
    )
