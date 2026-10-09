import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    host_participant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_video_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_playing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    state_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    participants = relationship("Participant", back_populates="room", cascade="all, delete-orphan")
