from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Identity, Text, text, Date, TIMESTAMP
from app.core.database import Base
from datetime import date, datetime, timezone

class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(
        secondary="user_roles",
        back_populates="roles"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    phone_number: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                 default=lambda: datetime.now(timezone.utc),
                                                 server_default=text("timezone('utc', now())"),
                                                 nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")
    organizers: Mapped[list["Organizer"]] = relationship(back_populates='users', secondary='organizers_users')


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
