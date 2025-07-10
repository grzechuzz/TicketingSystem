from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Identity, Text
from app.core.database import Base


class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Text] = mapped_column(unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(
        secondary="user_roles",
        backref="roles"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    first_name: Mapped[Text] = mapped_column(nullable=False)
    last_name: Mapped[Text] = mapped_column(nullable=False)
    email: Mapped[Text] = mapped_column(nullable=False, unique=True)
    phone_number: Mapped[Text] = mapped_column(nullable=True, unique=True)
    password_hash: Mapped[Text] = mapped_column(nullable=False)

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users"
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


