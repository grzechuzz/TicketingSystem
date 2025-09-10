import uuid
from datetime import datetime
from app.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Text, text, TIMESTAMP
from sqlalchemy.dialects.postgresql import INET, UUID


class AuthRefreshSession(Base):
    __tablename__ = "auth_refresh_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                 nullable=False,
                                                 server_default=text("timezone('utc', now())"))
    last_used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)

    user: Mapped['User'] = relationship(back_populates='refresh_sessions', lazy='joined')
