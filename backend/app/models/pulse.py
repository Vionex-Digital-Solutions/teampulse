"""PulseEntry model for daily mood/energy check-ins."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PulseEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A daily pulse check-in entry."""

    __tablename__ = "pulse_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    pulse_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mood: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-5 scale")
    energy: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-5 scale")
    has_blocker: Mapped[bool] = mapped_column(default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note_ar: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user = relationship("User", back_populates="pulse_entries")

    def __repr__(self) -> str:
        return f"<PulseEntry user={self.user_id} date={self.pulse_date} mood={self.mood}>"
