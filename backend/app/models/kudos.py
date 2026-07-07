"""Kudos model for peer-to-peer recognition."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Kudos(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A peer-to-peer kudos/recognition entry."""

    __tablename__ = "kudos"

    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="e.g., teamwork, innovation, mentorship, above_and_beyond",
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_ar: Mapped[str | None] = mapped_column(Text, nullable=True)

    sender = relationship("User", back_populates="kudos_sent", foreign_keys=[sender_id])
    receiver = relationship("User", back_populates="kudos_received", foreign_keys=[receiver_id])

    def __repr__(self) -> str:
        return f"<Kudos from={self.sender_id} to={self.receiver_id} cat={self.category}>"
