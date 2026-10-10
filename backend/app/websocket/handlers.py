from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

from pydantic import ValidationError

from sqlalchemy.orm import Session

from app.models.participant import Role

from app.schemas.websocket import WebSocketEvent

from app.services.permission_service import PermissionDenied, PermissionService

from app.services.room_service import RoomService

from app.services.sync_service import SyncService

from app.websocket.events import error_message, event_message

from app.websocket.manager import RoomManager
from app.schemas import participant

# ============================================================

# ACTION REQUEST STORAGE

# ============================================================

# In-memory storage for pending participant action requests.

#

# Structure:

# {

#     "ROOMCODE": {

#         "request-id": {

#             "requestId": "...",

#             "userId": "...",

#             "username": "...",

#             "action": "play",

#             "payload": {},

#             "timestamp": "...",

#             "status": "pending"

#         }

#     }

# }

ACTION_REQUESTS: dict[str, dict[str, dict]] = {}

# Requests older than this are considered stale.

ACTION_REQUEST_TTL_SECONDS = 300

class WebSocketHandler:

    def __init__(self, db: Session, manager: RoomManager):

        self.db = db

        self.manager = manager

        self.room_service = RoomService(db)

        self.sync_service = SyncService(db)

    
    def _require_host_or_moderator(self, role: Role) -> None:
        PermissionService.require_host_or_moderator(role)


    # ============================================================

    # CONNECTION

    # ============================================================

    async def run(

        self,

        websocket: WebSocket,

        room_code: str,

        participant_id: str,

    ) -> None:

        room = self.room_service.get_room(room_code)

        if room is None:

            await websocket.accept()

            await websocket.send_json(

                error_message(

                    "ROOM_NOT_FOUND",

                    "Room does not exist.",

                )

            )

            await websocket.close(code=1008)

            return

        participant = self.room_service.get_participant(

            participant_id,

            room.id,

        )

        if participant is None:

            await websocket.accept()

            await websocket.send_json(

                error_message(

                    "PARTICIPANT_NOT_FOUND",

                    "Participant session is invalid.",

                )

            )

            await websocket.close(code=1008)

            return

        await self.manager.connect(

            room.room_code,

            participant.id,

            websocket,

        )

        self.room_service.mark_online(

            participant,

            True,

        )

        # Send current playback state to the newly connected user.

        await websocket.send_json(

            self._sync_state(room)

        )

        # Tell existing users that somebody joined.

        await self.manager.broadcast(

            room.room_code,

            event_message(

                "user_joined",

                {

                    "userId": participant.id,

                    "username": participant.username,

                    "role": participant.role.value,

                    "online": True,

                },

            ),

            exclude=participant.id,

        )

        try:

            while True:

                raw = await websocket.receive_json()

                await self.handle_event(

                    room_code,

                    participant_id,

                    raw,

                )

        except WebSocketDisconnect:

            await self._disconnect(

                room_code,

                participant_id,

            )

        except Exception:

            await self._disconnect(

                room_code,

                participant_id,

            )

            raise

    # ============================================================

    # DISCONNECT

    # ============================================================

    async def _disconnect(

        self,

        room_code: str,

        participant_id: str,

    ) -> None:

        room = self.room_service.get_room(room_code)

        if room:

            participant = self.room_service.get_participant(

                participant_id,

                room.id,

            )

            if participant:

                self.room_service.mark_online(

                    participant,

                    False,

                )

                await self.manager.broadcast(

                    room.room_code,

                    event_message(

                        "user_left",

                        {

                            "userId": participant.id,

                            "username": participant.username,

                            "online": False,

                        },

                    ),

                    exclude=participant.id,

                )

        # Remove pending action requests belonging to the

        # disconnected participant.

        self._remove_requests_for_user(

            room_code,

            participant_id,

        )

        await self.manager.disconnect(

            room_code,

            participant_id,

        )

    # ============================================================

    # EVENT ROUTER

    # ============================================================

    async def handle_event(

        self,

        room_code: str,

        participant_id: str,

        raw: dict,

    ) -> None:

        try:

            event = WebSocketEvent.model_validate(raw)

        except ValidationError:

            await self.manager.send_to_user(

                room_code,

                participant_id,

                error_message(

                    "INVALID_EVENT",

                    "Malformed WebSocket event.",

                    None,

                ),

            )

            return

        room = self.room_service.get_room(room_code)

        participant = self.room_service.get_participant(

            participant_id,

            room.id if room else None,

        )

        if room is None or participant is None:

            await self.manager.send_to_user(

                room_code,

                participant_id,

                error_message(

                    "INVALID_SESSION",

                    "Room or participant session is invalid.",

                    event.request_id,

                ),

            )

            return

        try:

            # ====================================================

            # PLAYBACK CONTROLS

            # ====================================================

            if event.event in {

                "play",

                "pause",

                "seek",

                "change_video",

            }:

                PermissionService.require_playback_control(participant.role)

                await self._handle_playback(

                    room,

                    event,

                )

            # ====================================================

            # ASSIGN ROLE

            # ====================================================

            elif event.event == "assign_role":

                PermissionService.require_playback_control(participant.role)

                await self._assign_role(

                    room_code,

                    room.id,

                    event,

                )

            # ====================================================

            # REMOVE PARTICIPANT

            # ====================================================

            elif event.event == "remove_participant":
                self._require_host_or_moderator(participant.role)
                await self._remove_participant(
                    room_code,
                    room.id,
                    event,
                    participant.role,
                )

            # ====================================================

            # TRANSFER HOST

            # ====================================================

            elif event.event == "transfer_host":

                PermissionService.require_playback_control(participant.role)

                await self._transfer_host(

                    room_code,

                    room.id,

                    participant_id,

                    event,

                )

            # ====================================================

            # LEAVE ROOM

            # ====================================================

            elif event.event == "leave_room":

                await self._disconnect(

                    room_code,

                    participant_id,

                )

            # ====================================================

            # CHAT

            # ====================================================

            elif event.event == "chat_message":

                await self._handle_chat_message(

                    room_code,

                    participant_id,

                    participant.username,

                    event,

                )

            # ====================================================

            # REACTION

            # ====================================================

            elif event.event == "reaction":

                await self._handle_reaction(

                    room_code,

                    participant_id,

                    participant.username,

                    event,

                )

            # ====================================================

            # PARTICIPANT ACTION REQUEST

            # ====================================================

            elif event.event == "action_request":

                await self._handle_action_request(

                    room_code,

                    participant_id,

                    participant.username,

                    participant.role,

                    event,

                )

            # ====================================================

            # APPROVE ACTION REQUEST

            # ====================================================

            
            elif event.event == "approve_request":
                self._require_host_or_moderator(participant.role)
                await self._resolve_action_request(
                    room_code,
                    participant_id,
                    event,
                    approved=True,
                )


            # ====================================================

            # REJECT ACTION REQUEST

            # ====================================================

            
            elif event.event == "reject_request":
                self._require_host_or_moderator(participant.role)

                await self._resolve_action_request(
                    room_code,
                    participant_id,
                    event,
                    approved=False,
                )


            # ====================================================

            # UNKNOWN EVENT

            # ====================================================

            else:

                await self.manager.send_to_user(

                    room_code,

                    participant_id,

                    error_message(

                        "UNKNOWN_EVENT",

                        f"Unknown event '{event.event}'.",

                        event.request_id,

                    ),

                )

        except PermissionDenied as exc:

            await self.manager.send_to_user(

                room_code,

                participant_id,

                error_message(

                    "FORBIDDEN",

                    str(exc),

                    event.request_id,

                ),

            )

        except ValueError as exc:

            await self.manager.send_to_user(

                room_code,

                participant_id,

                error_message(

                    "INVALID_PAYLOAD",

                    str(exc),

                    event.request_id,

                ),

            )

    # ============================================================

    # ACTION REQUEST CREATION

    # ============================================================

    async def _handle_action_request(

        self,

        room_code: str,

        participant_id: str,

        username: str,

        role: Role,

        event: WebSocketEvent,

    ) -> None:

        # Only normal participants need to request actions.

        if role != Role.PARTICIPANT:

            raise ValueError(

                "Only participants need to request playback actions."

            )

        # Remove expired requests before processing a new one.

        self._cleanup_stale_requests(room_code)

        action = event.payload.get("action")

        payload = event.payload.get("payload", {})

        allowed_actions = {

            "play",

            "pause",

            "seek",

            "change_video",

        }

        if action not in allowed_actions:

            raise ValueError(

                "Unsupported action request."

            )

        if not isinstance(payload, dict):

            raise ValueError(

                "Action payload must be an object."

            )

        request_id = event.request_id

        if not request_id:

            raise ValueError(

                "Action request requires a request ID."

            )

        room_requests = ACTION_REQUESTS.setdefault(

            room_code,

            {},

        )

        # Prevent duplicate request IDs.

        if request_id in room_requests:

            raise ValueError(

                "This action request already exists."

            )

        # Prevent the same participant from creating

        # multiple pending requests for the same action.

        for request in room_requests.values():

            if (

                request["status"] == "pending"

                and request["userId"] == participant_id

                and request["action"] == action

            ):

                raise ValueError(

                    "You already have a pending request for this action."

                )

        request = {

            "requestId": request_id,

            "userId": participant_id,

            "username": username,

            "action": action,

            "payload": payload,

            "timestamp": datetime.now(

                timezone.utc

            ).isoformat(),

            "status": "pending",

        }

        room_requests[request_id] = request

        # Send the request to every Host and Moderator.

        for user_id in self.manager.get_room_users(

            room_code

        ):

            user = self.room_service.get_participant(

                user_id

            )

            if user is None:

                continue

            if user.role in {

                Role.HOST,

                Role.MODERATOR,

            }:

                await self.manager.send_to_user(

                    room_code,

                    user_id,

                    event_message(

                        "action_requested",

                        request,

                        request_id,

                    ),

                )

    # ============================================================

    # ACTION REQUEST APPROVE / REJECT

    # ============================================================

    async def _resolve_action_request(

        self,

        room_code: str,

        resolver_id: str,

        event: WebSocketEvent,

        approved: bool,

    ) -> None:

        # Remove old requests first.

        self._cleanup_stale_requests(room_code)

        request_id = event.payload.get(

            "requestId"

        )

        if not request_id:

            raise ValueError(

                "Request ID is required."

            )

        room_requests = ACTION_REQUESTS.get(

            room_code,

            {},

        )

        request = room_requests.get(

            request_id

        )

        if request is None:

            raise ValueError(

                "Action request does not exist or has expired."

            )

        if request["status"] != "pending":

            raise ValueError(

                "This action request has already been resolved."

            )

        room = self.room_service.get_room(

            room_code

        )

        if room is None:

            raise ValueError(

                "Room does not exist."

            )

        requester = self.room_service.get_participant(

            request["userId"],

            room.id,

        )

        if requester is None:

            request["status"] = "rejected"

            await self.manager.send_to_user(

                room_code,

                request["userId"],

                event_message(

                    "action_request_resolved",

                    {

                        **request,

                        "status": "rejected",

                        "resolvedBy": resolver_id,

                    },

                    request_id,

                ),

            )

            del room_requests[request_id]

            return

        # If requester is no longer connected, do not execute

        # the request.

        if not self.manager.is_connected(

            room_code,

            request["userId"],

        ):

            request["status"] = "rejected"

            resolved_payload = {

                **request,

                "status": "rejected",

                "resolvedBy": resolver_id,

            }

            # Notify Host/Moderator who resolved it.

            await self.manager.send_to_user(

                room_code,

                resolver_id,

                event_message(

                    "action_request_resolved",

                    resolved_payload,

                    request_id,

                ),

            )

            del room_requests[request_id]

            return

        # ========================================================

        # APPROVED

        # ========================================================

        if approved:

            playback_event = WebSocketEvent(

                event=request["action"],

                payload=request["payload"],

                request_id=request_id,

            )

            # Execute the requested action through the same

            # playback pipeline used by Host/Moderator controls.

            await self._handle_playback(

                room,

                playback_event,

            )

            request["status"] = "approved"

        # ========================================================

        # REJECTED

        # ========================================================

        else:

            request["status"] = "rejected"

        resolved_payload = {

            **request,

            "status": request["status"],

            "resolvedBy": resolver_id,

        }

        # Tell the participant who created the request.

        await self.manager.send_to_user(

            room_code,

            request["userId"],

            event_message(

                "action_request_resolved",

                resolved_payload,

                request_id,

            ),

        )

        # Tell all connected Host/Moderators as well.

        for user_id in self.manager.get_room_users(

            room_code

        ):

            if user_id == request["userId"]:

                continue

            user = self.room_service.get_participant(

                user_id,

                room.id,

            )

            if user and user.role in {

                Role.HOST,

                Role.MODERATOR,

            }:

                await self.manager.send_to_user(

                    room_code,

                    user_id,

                    event_message(

                        "action_request_resolved",

                        resolved_payload,

                        request_id,

                    ),

                )

        # Remove resolved request from memory.

        del room_requests[request_id]

        if not room_requests:

            ACTION_REQUESTS.pop(

                room_code,

                None,

            )

    # ============================================================

    # CLEANUP STALE REQUESTS

    # ============================================================

    def _cleanup_stale_requests(

        self,

        room_code: str,

    ) -> None:

        room_requests = ACTION_REQUESTS.get(

            room_code

        )

        if not room_requests:

            return

        now = datetime.now(

            timezone.utc

        )

        expired_request_ids = []

        for request_id, request in room_requests.items():

            timestamp_text = request.get(

                "timestamp"

            )

            if not timestamp_text:

                expired_request_ids.append(

                    request_id

                )

                continue

            try:

                created_at = datetime.fromisoformat(

                    timestamp_text

                )

                # Ensure timezone awareness.

                if created_at.tzinfo is None:

                    created_at = created_at.replace(

                        tzinfo=timezone.utc

                    )

                age = (

                    now - created_at

                ).total_seconds()

                if age > ACTION_REQUEST_TTL_SECONDS:

                    expired_request_ids.append(

                        request_id

                    )

            except ValueError:

                expired_request_ids.append(

                    request_id

                )

        for request_id in expired_request_ids:

            room_requests.pop(

                request_id,

                None,

            )

        if not room_requests:

            ACTION_REQUESTS.pop(

                room_code,

                None,

            )

    # ============================================================

    # REMOVE USER'S PENDING REQUESTS

    # ============================================================

    def _remove_requests_for_user(

        self,

        room_code: str,

        participant_id: str,

    ) -> None:

        room_requests = ACTION_REQUESTS.get(

            room_code

        )

        if not room_requests:

            return

        request_ids = [

            request_id

            for request_id, request in room_requests.items()

            if request.get("userId") == participant_id

        ]

        for request_id in request_ids:

            room_requests.pop(

                request_id,

                None,

            )

        if not room_requests:

            ACTION_REQUESTS.pop(

                room_code,

                None,

            )

    # ============================================================

    # CHAT

    # ============================================================

    async def _handle_chat_message(

        self,

        room_code: str,

        participant_id: str,

        username: str,

        event: WebSocketEvent,

    ) -> None:

        message = event.payload.get(

            "message"

        )

        if not isinstance(message, str):

            raise ValueError(

                "Chat message must be text."

            )

        message = message.strip()

        if not message:

            raise ValueError(

                "Chat message cannot be empty."

            )

        if len(message) > 500:

            raise ValueError(

                "Chat message cannot exceed 500 characters."

            )

        await self.manager.broadcast(

            room_code,

            event_message(

                "chat_message",

                {

                    "userId": participant_id,

                    "username": username,

                    "message": message,

                },

                event.request_id,

            ),

        )

    # ============================================================

    # REACTIONS

    # ============================================================

    async def _handle_reaction(

        self,

        room_code: str,

        participant_id: str,

        username: str,

        event: WebSocketEvent,

    ) -> None:

        reaction = event.payload.get(

            "reaction"

        )

        allowed_reactions = {

            "❤️",

            "😂",

            "🔥",

            "👏",

            "😮",

        }

        if reaction not in allowed_reactions:

            raise ValueError(

                "Unsupported reaction."

            )

        await self.manager.broadcast(

            room_code,

            event_message(

                "reaction",

                {

                    "userId": participant_id,

                    "username": username,

                    "reaction": reaction,

                },

                event.request_id,

            ),

        )

    # ============================================================

    # PLAYBACK

    # ============================================================

    async def _handle_playback(

        self,

        room,

        event: WebSocketEvent,

    ) -> None:

        current_time = (

            self.sync_service.effective_current_time(

                room

            )

        )

        # ========================================================

        # PLAY

        # ========================================================

        if event.event == "play":

            self.sync_service.update_playback(

                room,

                is_playing=True,

                current_time=current_time,

            )

            await self.manager.broadcast(

                room.room_code,

                event_message(

                    "play",

                    self._state_payload(room),

                ),

            )

        # ========================================================

        # PAUSE

        # ========================================================

        elif event.event == "pause":

            self.sync_service.update_playback(

                room,

                is_playing=False,

                current_time=current_time,

            )

            await self.manager.broadcast(

                room.room_code,

                event_message(

                    "pause",

                    self._state_payload(room),

                ),

            )

        # ========================================================

        # SEEK

        # ========================================================

        elif event.event == "seek":

            time_value = event.payload.get(

                "time"

            )

            validated_time = (

                self.sync_service.validate_time(

                    time_value

                )

            )

            self.sync_service.update_playback(

                room,

                is_playing=room.is_playing,

                current_time=validated_time,

            )

            await self.manager.broadcast(

                room.room_code,

                event_message(

                    "seek",

                    self._state_payload(room),

                ),

            )

        # ========================================================

        # CHANGE VIDEO

        # ========================================================

        elif event.event == "change_video":

            video_id = event.payload.get(

                "videoId"

            )

            self.sync_service.change_video(

                room,

                video_id,

            )

            await self.manager.broadcast(

                room.room_code,

                event_message(

                    "video_changed",

                    self._state_payload(room),

                ),

            )

    # ============================================================

    # ASSIGN ROLE

    # ============================================================

    async def _assign_role(

        self,

        room_code: str,

        room_id: str,

        event: WebSocketEvent,

    ) -> None:

        target_id = event.payload.get(

            "userId"

        )

        role_value = event.payload.get(

            "role"

        )

        target = self.room_service.get_participant(

            target_id,

            room_id,

        )

        if target is None:

            raise ValueError(

                "Target participant does not exist."

            )

        if target.role == Role.HOST:

            raise ValueError(

                "The host role cannot be assigned this way."

            )

        if role_value not in {

            Role.MODERATOR.value,

            Role.PARTICIPANT.value,

        }:

            raise ValueError(

                "Role must be MODERATOR or PARTICIPANT."

            )

        target.role = Role(role_value)

        self.db.commit()

        await self.manager.broadcast(

            room_code,

            event_message(

                "role_assigned",

                {

                    "userId": target.id,

                    "username": target.username,

                    "role": target.role.value,

                },

                event.request_id,

            ),

        )

    # ============================================================

    # REMOVE PARTICIPANT

    # ============================================================

    async def _remove_participant(

        self,

        room_code: str,

        room_id: str,

        event: WebSocketEvent,

        actor_role: Role,

    ) -> None:

        target_id = event.payload.get(

            "userId"

        )

        target = self.room_service.get_participant(

            target_id,

            room_id,

        )

        if target is None:

            raise ValueError(

                "Target participant does not exist."

            )

        if target.role == Role.HOST:
            raise PermissionDenied("The host cannot be removed.")

        if actor_role == Role.MODERATOR and target.role == Role.MODERATOR:
            raise PermissionDenied("Moderators cannot remove other moderators.")

        username = target.username

        # Remove pending requests for this user.

        self._remove_requests_for_user(

            room_code,

            target_id,

        )

        self.db.delete(target)

        self.db.commit()

        # Tell the removed user.

        await self.manager.send_to_user(

            room_code,

            target_id,

            event_message(

                "participant_removed",

                {

                    "userId": target_id,

                    "username": username,

                },

                event.request_id,

            ),

        )

        # Disconnect their websocket.

        await self.manager.disconnect(

            room_code,

            target_id,

        )

        # Inform everybody else.

        await self.manager.broadcast(

            room_code,

            event_message(

                "participant_removed",

                {

                    "userId": target_id,

                    "username": username,

                },

                event.request_id,

            ),

            exclude=target_id,

        )

    # ============================================================

    # TRANSFER HOST

    # ============================================================

    async def _transfer_host(

        self,

        room_code: str,

        room_id: str,

        current_host_id: str,

        event: WebSocketEvent,

    ) -> None:

        target_id = event.payload.get(

            "userId"

        )

        target = self.room_service.get_participant(

            target_id,

            room_id,

        )

        current_host = self.room_service.get_participant(

            current_host_id,

            room_id,

        )

        if target is None:

            raise ValueError(

                "Target participant does not exist."

            )

        if (

            current_host is None

            or current_host.role != Role.HOST

        ):

            raise PermissionDenied(

                "Only the current host can transfer host ownership."

            )

        if target.id == current_host.id:

            raise ValueError(

                "The target is already the host."

            )

        current_host.role = Role.PARTICIPANT

        target.role = Role.HOST

        room = self.room_service.get_room(

            room_code

        )

        if room is None:

            raise ValueError(

                "Room does not exist."

            )

        room.host_participant_id = target.id

        self.db.commit()

        await self.manager.broadcast(

            room_code,

            event_message(

                "host_transferred",

                {

                    "previousHostId": current_host.id,

                    "newHostId": target.id,

                },

                event.request_id,

            ),

        )

    # ============================================================

    # STATE PAYLOAD

    # ============================================================

    def _state_payload(

        self,

        room,

    ) -> dict:

        return {

            "roomId": room.id,

            "videoId": room.current_video_id,

            "isPlaying": room.is_playing,

            "currentTime": room.current_time,

            "updatedAt": room.state_updated_at.isoformat(),

            "stateVersion": room.state_version,

        }

    # ============================================================

    # INITIAL SYNC STATE

    # ============================================================

    def _sync_state(

        self,

        room,

    ) -> dict:

        return event_message(

            "sync_state",

            self._state_payload(room),

        )
