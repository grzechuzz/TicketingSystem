from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Identity, Text, ForeignKey
from app.core.database import Base
from app.domain import Address

class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address_id: Mapped[int | None] = mapped_column(
                                        ForeignKey("addresses.id", ondelete='SET NULL'),
                                        nullable=True,
                                        unique=True)

    address: Mapped['Address'] = relationship(back_populates="venues", lazy='selectin')
