from fastapi.testclient import TestClient

from app.database.connection import Base, engine
from app.main import app


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_lookup_room():
    response = client.post("/api/rooms", json={"username": "Aman"})
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "HOST"
    assert len(data["room_code"]) == 6

    lookup = client.get(f"/api/rooms/{data['room_code']}")
    assert lookup.status_code == 200
    assert lookup.json()["exists"] is True
    assert lookup.json()["participant_count"] == 1


def test_join_room():
    created = client.post("/api/rooms", json={"username": "HostUser"}).json()
    response = client.post(
        f"/api/rooms/{created['room_code']}/join",
        json={"username": "Participant"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "PARTICIPANT"


def test_duplicate_username_is_rejected():
    created = client.post("/api/rooms", json={"username": "Host2"}).json()
    with client.websocket_connect(
        f"/ws/rooms/{created['room_code']}/{created['participant_id']}"
    ):
        response = client.post(
            f"/api/rooms/{created['room_code']}/join",
            json={"username": "Host2"},
        )
        assert response.status_code == 409
