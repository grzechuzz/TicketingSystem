from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Identity, Text, Integer, ForeignKey, CheckConstraint, Boolean, TIMESTAMP, func, Enum
from app.core.database import Base
from datetime import datetime
import enum


class EventStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    ON_SALE = "ON_SALE"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    organizer_id: Mapped[int] = mapped_column(
        ForeignKey("organizers.id", ondelete='RESTRICT'),
        nullable=False,
        index=True)
    venue_id: Mapped[int] = mapped_column(
        ForeignKey("venues.id", ondelete='RESTRICT'),
        nullable=False,
        index=True
    )
    event_start: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    event_end: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    sales_start: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    sales_end: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    max_tickets_per_user: Mapped[int] = mapped_column(Integer, nullable=True)
    age_restriction: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    holder_data_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"),
        nullable=False,
        default=EventStatus.PLANNED
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    venue: Mapped['Venue'] = relationship(back_populates='events', lazy='selectin')
    organizer: Mapped['Organizer'] = relationship(back_populates='events', lazy='selectin')

    __table_args__ = (
        CheckConstraint("event_end > event_start", name="chk_event_time_range"),
        CheckConstraint("sales_end >= sales_start", name="chk_sales_range"),
        CheckConstraint("sales_end <= event_start", name="chk_sales_vs_event"),
    )
