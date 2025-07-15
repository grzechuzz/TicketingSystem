from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Identity, Text, String
from app.core.database import Base

class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    street: Mapped[str] = mapped_column(Text, nullable=False)
    postal_code: Mapped[str] = mapped_column(String(12), nullable=False)
    building_number: Mapped[str] = mapped_column(String(10), nullable=False)
    apartment_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)

    organizers: Mapped[list['Organizer']] = relationship(back_populates="address")
