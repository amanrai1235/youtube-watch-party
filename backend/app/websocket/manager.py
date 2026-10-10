from collections import defaultdict

from fastapi import WebSocket


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self._roles: dict[str, dict[str, str]] = defaultdict(dict)

    async def connect(
        self,
        room_code: str,
        participant_id: str,
        websocket: WebSocket,
        role: str = "PARTICIPANT",
    ) -> None:
        await websocket.accept()
        self._rooms[room_code][participant_id] = websocket
        role_value = getattr(role, "value", role)
        self._roles[room_code][participant_id] = str(role_value).strip().upper()

    def set_role(self, room_code: str, participant_id: str, role: str) -> None:
        if room_code in self._roles:
            role_value = getattr(role, "value", role)
            self._roles[room_code][participant_id] = str(role_value).strip().upper()

    def get_role(self, room_code: str, participant_id: str) -> str | None:
        return self._roles.get(room_code, {}).get(participant_id)

    def get_privileged_users(self, room_code: str) -> list[str]:
        roles = self._roles.get(room_code, {})
        return [uid for uid, r in roles.items() if r in {"HOST", "MODERATOR"}]

    async def disconnect(self, room_code: str, participant_id: str) -> None:
        room = self._rooms.get(room_code)
        if not room:
            return
        room.pop(participant_id, None)
        self._roles.get(room_code, {}).pop(participant_id, None)
        if not room:
            self._rooms.pop(room_code, None)
            self._roles.pop(room_code, None)

    async def send_to_user(self, room_code: str, participant_id: str, message: dict) -> bool:
        websocket = self._rooms.get(room_code, {}).get(participant_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            await self.disconnect(room_code, participant_id)
            return False

    async def broadcast(self, room_code: str, message: dict, exclude: str | None = None) -> None:
        connections = list(self._rooms.get(room_code, {}).items())
        for participant_id, websocket in connections:
            if participant_id == exclude:
                continue
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(room_code, participant_id)

    def get_room_users(self, room_code: str) -> list[str]:
        return list(self._rooms.get(room_code, {}).keys())

    def is_connected(self, room_code: str, participant_id: str) -> bool:
        return participant_id in self._rooms.get(room_code, {})


room_manager = RoomManager()
