"""User model."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A TeamPulse user (team member)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name_ar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locale: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    pulse_entries = relationship("PulseEntry", back_populates="user", lazy="selectin")
    standup_entries = relationship("StandupEntry", back_populates="user", lazy="selectin")
    kudos_sent = relationship(
        "Kudos", back_populates="sender", foreign_keys="Kudos.sender_id", lazy="selectin"
    )
    kudos_received = relationship(
        "Kudos", back_populates="receiver", foreign_keys="Kudos.receiver_id", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
