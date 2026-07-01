"""StandupEntry model for async daily standups."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StandupEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A daily async standup entry."""

    __tablename__ = "standup_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    standup_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    yesterday: Mapped[str] = mapped_column(Text, nullable=False)
    today: Mapped[str] = mapped_column(Text, nullable=False)
    blockers: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Comma-separated tags")

    user = relationship("User", back_populates="standup_entries")

    def __repr__(self) -> str:
        return f"<StandupEntry user={self.user_id} date={self.standup_date}>"
