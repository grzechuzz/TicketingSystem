from sqlalchemy import Identity, Text, String, ForeignKey, UniqueConstraint, TIMESTAMP, Table, Column
from app.core.database import Base
from sqlalchemy.orm import mapped_column, Mapped, relationship
from datetime import datetime, timezone

class Organizer(Base):
    __tablename__ = 'organizers'
    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    phone_number: Mapped[str] = mapped_column(Text, nullable=False)
    address_id: Mapped[int | None] = mapped_column(ForeignKey('addresses.id', ondelete='SET NULL'), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    registration_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True, unique=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                 default=lambda: datetime.now(timezone.utc),
                                                 nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint('country_code', 'registration_number', name='uq_organizers_country_reg_number'),
    )

    address: Mapped['Address'] = relationship(back_populates='organizers')
    users: Mapped[list['User']] = relationship(back_populates='organizers', secondary='organizers_users')


organizers_users = Table(
    'organizers_users',
    Base.metadata,
    Column('user_id', ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('organizer_id', ForeignKey('organizers.id', ondelete='CASCADE'), primary_key=True),
)
