from datetime import datetime

from pydantic import BaseModel

from app.models.participant import Role


class ParticipantResponse(BaseModel):
    id: str
    username: str
    role: Role
    online: bool
    joined_at: datetime
    last_seen: datetime
