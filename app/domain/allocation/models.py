from app.core.database import Base
from sqlalchemy import Identity, ForeignKey, CheckConstraint, UniqueConstraint, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EventSector(Base):
    __tablename__ = 'event_sectors'

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id"), nullable=False, index=True)
    tickets_left: Mapped[int | None] = mapped_column(nullable=True)

    event = relationship("Event", back_populates="event_sectors", lazy="selectin")
    sector = relationship("Sector", back_populates="event_sectors", lazy="selectin")
    event_ticket_types: Mapped[list['EventTicketType']] = relationship(back_populates="event_sector", lazy="selectin")

    __table_args__ = (
        UniqueConstraint('event_id', 'sector_id', name='uq_event_sector'),
        CheckConstraint("tickets_left >= 0", name="chk_tickets_left")
    )
