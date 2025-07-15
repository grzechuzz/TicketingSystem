from sqlalchemy import Table, Column, ForeignKey
from app.core.database import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id",  ForeignKey("users.id",  ondelete="CASCADE"), primary_key=True),
    Column("role_id",  ForeignKey("roles.id",  ondelete="CASCADE"), primary_key=True),
)

organizers_users = Table(
    "organizers_users",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("organizer_id", ForeignKey("organizers.id", ondelete="CASCADE"), primary_key=True),
)
