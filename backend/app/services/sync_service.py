import math
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.room import Room

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SyncService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def validate_video_id(video_id: str) -> str:
        if not isinstance(video_id, str) or not YOUTUBE_ID_RE.fullmatch(video_id):
            raise ValueError("Invalid YouTube video ID.")
        return video_id

    @staticmethod
    def validate_time(value: float) -> float:
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("Playback time must be a finite number greater than or equal to zero.")
        return float(value)

    def update_playback(self, room: Room, *, is_playing: bool, current_time: float) -> None:
        room.is_playing = is_playing
        room.current_time = self.validate_time(current_time)
        room.state_updated_at = utc_now()
        room.state_version += 1
        self.db.commit()

    def change_video(self, room: Room, video_id: str) -> None:
        room.current_video_id = self.validate_video_id(video_id)
        room.current_time = 0.0
        room.is_playing = False
        room.state_updated_at = utc_now()
        room.state_version += 1
        self.db.commit()

    @staticmethod
    def effective_current_time(room: Room) -> float:
        if not room.is_playing:
            return room.current_time
        updated_at = room.state_updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        elapsed = (utc_now() - updated_at).total_seconds()
        return max(0.0, room.current_time + elapsed)
