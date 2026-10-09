from fastapi.testclient import TestClient

from app.database.connection import Base, engine
from app.main import app


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def create_room_and_participant():
    host = client.post("/api/rooms", json={"username": "HostUser"}).json()
    participant = client.post(
        f"/api/rooms/{host['room_code']}/join",
        json={"username": "Viewer"},
    ).json()
    return host, participant


def test_participant_cannot_play():
    host, participant = create_room_and_participant()

    with client.websocket_connect(
        f"/ws/rooms/{host['room_code']}?participant_id={participant['participant_id']}"
    ) as ws:
        initial = ws.receive_json()
        assert initial["event"] == "sync_state"

        ws.send_json({"event": "play", "requestId": "req-1", "payload": {}})
        error = ws.receive_json()
        assert error["event"] == "error"
        assert error["payload"]["code"] == "FORBIDDEN"


def test_host_can_change_video_and_state_is_broadcast():
    host, _participant = create_room_and_participant()

    with client.websocket_connect(
        f"/ws/rooms/{host['room_code']}?participant_id={host['participant_id']}"
    ) as ws:
        initial = ws.receive_json()
        assert initial["event"] == "sync_state"

        ws.send_json(
            {
                "event": "change_video",
                "requestId": "req-2",
                "payload": {"videoId": "dQw4w9WgXcQ"},
            }
        )
        changed = ws.receive_json()
        assert changed["event"] == "video_changed"
        assert changed["payload"]["videoId"] == "dQw4w9WgXcQ"
        assert changed["payload"]["currentTime"] == 0.0
        assert changed["payload"]["isPlaying"] is False
