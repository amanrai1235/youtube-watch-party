from typing import Any, Literal

from pydantic import BaseModel, Field


EventName = Literal[
    "join_room",
    "leave_room",
    "play",
    "pause",
    "seek",
    "change_video",
    "assign_role",
    "remove_participant",
    "transfer_host",
    "action_request",
    "approve_request",
    "reject_request",
    "chat_message",
    "reaction",
]


class WebSocketEvent(BaseModel):
    event: EventName
    request_id: str | None = Field(default=None, alias="requestId")
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "extra": "forbid"}
