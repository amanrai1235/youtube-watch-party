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
        f"/ws/rooms/{host['room_code']}/{participant['participant_id']}"
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
        f"/ws/rooms/{host['room_code']}/{host['participant_id']}"
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


def test_moderator_can_approve_action_request():
    host = client.post("/api/rooms", json={"username": "HostA"}).json()
    room_code = host["room_code"]

    mod_user = client.post(
        f"/api/rooms/{room_code}/join",
        json={"username": "ModUser"},
    ).json()

    viewer = client.post(
        f"/api/rooms/{room_code}/join",
        json={"username": "ViewerA"},
    ).json()

    with client.websocket_connect(f"/ws/rooms/{room_code}/{host['participant_id']}") as ws_host, \
         client.websocket_connect(f"/ws/rooms/{room_code}/{mod_user['participant_id']}") as ws_mod, \
         client.websocket_connect(f"/ws/rooms/{room_code}/{viewer['participant_id']}") as ws_viewer:

        # Drain initial messages
        ws_host.receive_json()  # sync_state
        ws_host.receive_json()  # user_joined (ModUser)
        ws_host.receive_json()  # user_joined (ViewerA)

        ws_mod.receive_json()   # sync_state
        ws_mod.receive_json()   # user_joined (ViewerA)

        ws_viewer.receive_json()  # sync_state

        # Host promotes ModUser to MODERATOR
        ws_host.send_json({
            "event": "assign_role",
            "requestId": "req-promote",
            "payload": {
                "userId": mod_user["participant_id"],
                "role": "MODERATOR",
            },
        })

        role_msg_host = ws_host.receive_json()
        assert role_msg_host["event"] == "role_assigned"
        role_msg_mod = ws_mod.receive_json()
        assert role_msg_mod["event"] == "role_assigned"
        ws_viewer.receive_json()  # role_assigned

        # Viewer requests 'play'
        ws_viewer.send_json({
            "event": "action_request",
            "requestId": "play-req-1",
            "payload": {
                "action": "play",
                "payload": {},
            },
        })

        # Both Host and Moderator must receive the action request
        host_req_msg = ws_host.receive_json()
        assert host_req_msg["event"] == "action_requested"
        assert host_req_msg["payload"]["action"] == "play"

        mod_req_msg = ws_mod.receive_json()
        assert mod_req_msg["event"] == "action_requested"
        assert mod_req_msg["payload"]["action"] == "play"
        assert mod_req_msg["payload"]["username"] == "ViewerA"

        # MODERATOR approves the request
        ws_mod.send_json({
            "event": "approve_request",
            "requestId": "req-appr-1",
            "payload": {
                "requestId": "play-req-1",
            },
        })

        # Host receives playback 'play' event and resolution
        host_play_msg = ws_host.receive_json()
        assert host_play_msg["event"] == "play"
        host_res_msg = ws_host.receive_json()
        assert host_res_msg["event"] == "action_request_resolved"
        assert host_res_msg["payload"]["status"] == "approved"

        # Mod receives playback 'play' event and resolution
        mod_play_msg = ws_mod.receive_json()
        assert mod_play_msg["event"] == "play"
        mod_res_msg = ws_mod.receive_json()
        assert mod_res_msg["event"] == "action_request_resolved"
        assert mod_res_msg["payload"]["status"] == "approved"

        # Viewer receives playback 'play' and resolution
        viewer_play_msg = ws_viewer.receive_json()
        assert viewer_play_msg["event"] == "play"
        viewer_res_msg = ws_viewer.receive_json()
        assert viewer_res_msg["event"] == "action_request_resolved"
        assert viewer_res_msg["payload"]["status"] == "approved"


def test_moderator_can_reject_action_request():
    host = client.post("/api/rooms", json={"username": "HostB"}).json()
    room_code = host["room_code"]

    mod_user = client.post(
        f"/api/rooms/{room_code}/join",
        json={"username": "ModUserB"},
    ).json()

    viewer = client.post(
        f"/api/rooms/{room_code}/join",
        json={"username": "ViewerB"},
    ).json()

    with client.websocket_connect(f"/ws/rooms/{room_code}/{host['participant_id']}") as ws_host, \
         client.websocket_connect(f"/ws/rooms/{room_code}/{mod_user['participant_id']}") as ws_mod, \
         client.websocket_connect(f"/ws/rooms/{room_code}/{viewer['participant_id']}") as ws_viewer:

        # Drain initial messages
        ws_host.receive_json()
        ws_host.receive_json()
        ws_host.receive_json()
        ws_mod.receive_json()
        ws_mod.receive_json()
        ws_viewer.receive_json()

        # Host promotes ModUserB to MODERATOR
        ws_host.send_json({
            "event": "assign_role",
            "requestId": "req-promote-2",
            "payload": {
                "userId": mod_user["participant_id"],
                "role": "MODERATOR",
            },
        })
        ws_host.receive_json()
        ws_mod.receive_json()
        ws_viewer.receive_json()

        # Viewer requests 'pause'
        ws_viewer.send_json({
            "event": "action_request",
            "requestId": "pause-req-1",
            "payload": {
                "action": "pause",
                "payload": {},
            },
        })

        ws_host.receive_json()  # action_requested
        mod_req_msg = ws_mod.receive_json()  # action_requested
        assert mod_req_msg["event"] == "action_requested"
        assert mod_req_msg["payload"]["action"] == "pause"

        # MODERATOR rejects the request
        ws_mod.send_json({
            "event": "reject_request",
            "requestId": "req-rej-1",
            "payload": {
                "requestId": "pause-req-1",
            },
        })

        # Resolution broadcast to Viewer, Mod, and Host
        host_res = ws_host.receive_json()
        assert host_res["event"] == "action_request_resolved"
        assert host_res["payload"]["status"] == "rejected"

        mod_res = ws_mod.receive_json()
        assert mod_res["event"] == "action_request_resolved"
        assert mod_res["payload"]["status"] == "rejected"

        viewer_res = ws_viewer.receive_json()
        assert viewer_res["event"] == "action_request_resolved"
        assert viewer_res["payload"]["status"] == "rejected"


def test_moderator_can_control_playback():
    host = client.post("/api/rooms", json={"username": "HostC"}).json()
    room_code = host["room_code"]

    mod_user = client.post(
        f"/api/rooms/{room_code}/join",
        json={"username": "ModUserC"},
    ).json()

    with client.websocket_connect(f"/ws/rooms/{room_code}/{host['participant_id']}") as ws_host, \
         client.websocket_connect(f"/ws/rooms/{room_code}/{mod_user['participant_id']}") as ws_mod:

        ws_host.receive_json()  # sync_state
        ws_host.receive_json()  # user_joined
        ws_mod.receive_json()   # sync_state

        # Host promotes to MODERATOR
        ws_host.send_json({
            "event": "assign_role",
            "requestId": "req-promote-3",
            "payload": {
                "userId": mod_user["participant_id"],
                "role": "MODERATOR",
            },
        })
        ws_host.receive_json()
        ws_mod.receive_json()

        # Moderator can directly play
        ws_mod.send_json({"event": "play", "requestId": "mod-play", "payload": {}})
        play_host = ws_host.receive_json()
        assert play_host["event"] == "play"
        play_mod = ws_mod.receive_json()
        assert play_mod["event"] == "play"

        # Moderator can directly seek
        ws_mod.send_json({"event": "seek", "requestId": "mod-seek", "payload": {"time": 42.0}})
        seek_host = ws_host.receive_json()
        assert seek_host["event"] == "seek"
        assert seek_host["payload"]["currentTime"] == 42.0

        # Moderator can directly change video
        ws_mod.send_json({
            "event": "change_video",
            "requestId": "mod-vid",
            "payload": {"videoId": "dQw4w9WgXcQ"},
        })
        vid_host = ws_host.receive_json()
        assert vid_host["event"] == "video_changed"
        assert vid_host["payload"]["videoId"] == "dQw4w9WgXcQ"
