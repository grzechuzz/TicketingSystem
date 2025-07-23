from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import Identity, Text, ForeignKey, Boolean, TIMESTAMP, Integer, UniqueConstraint, CheckConstraint
from app.core.database import Base
from app.domain import Address
from datetime import datetime


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id", ondelete='RESTRICT'),
                                            unique=True,
                                            nullable=False)

    address: Mapped['Address'] = relationship(back_populates="venues", lazy='selectin')
    sectors: Mapped[list['Sector']] = relationship(back_populates="venue", lazy='selectin')


class Sector(Base):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_ga: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    base_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    venue: Mapped['Venue'] = relationship(back_populates="sectors", lazy='selectin')
    __table_args__ = (
        UniqueConstraint("venue_id", "name", name="uq_sector_venue_name"),
        CheckConstraint("base_capacity > 0", name="chk_sector_base_capacity"),
    )
