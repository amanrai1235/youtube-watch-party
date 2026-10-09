from typing import Any


def event_message(event: str, payload: dict[str, Any] | None = None, request_id: str | None = None) -> dict:
    message = {"event": event, "payload": payload or {}}
    if request_id:
        message["requestId"] = request_id
    return message


def error_message(code: str, message: str, request_id: str | None = None) -> dict:
    return event_message("error", {"code": code, "message": message}, request_id)
