from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.participant import Role


class CreateRoomRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)


class JoinRoomRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40)


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: str
    room_code: str
    participant_id: str
    role: Role


class RoomLookupResponse(BaseModel):
    room_id: str
    room_code: str
    participant_count: int
    exists: bool


class RoomStateResponse(BaseModel):
    room_id: str
    room_code: str
    current_video_id: str | None
    is_playing: bool
    current_time: float
    state_updated_at: datetime
    state_version: int
