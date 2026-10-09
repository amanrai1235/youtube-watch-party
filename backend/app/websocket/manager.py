from collections import defaultdict

from fastapi import WebSocket


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def connect(self, room_code: str, participant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[room_code][participant_id] = websocket

    async def disconnect(self, room_code: str, participant_id: str) -> None:
        room = self._rooms.get(room_code)
        if not room:
            return
        room.pop(participant_id, None)
        if not room:
            self._rooms.pop(room_code, None)

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
