from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.participant import Participant
from app.schemas.room import (
    CreateRoomRequest,
    JoinRoomRequest,
    RoomLookupResponse,
    RoomResponse,
    RoomStateResponse,
)
from app.services.room_service import RoomService

router = APIRouter(prefix="/api", tags=["rooms"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(payload: CreateRoomRequest, db: Session = Depends(get_db)) -> RoomResponse:
    service = RoomService(db)
    room, participant = service.create_room(payload.username)
    return RoomResponse(
        room_id=room.id,
        room_code=room.room_code,
        participant_id=participant.id,
        role=participant.role,
    )


@router.get("/rooms/{room_code}", response_model=RoomLookupResponse)
def lookup_room(room_code: str, db: Session = Depends(get_db)) -> RoomLookupResponse:
    service = RoomService(db)
    room = service.get_room(room_code)
    if room is None:
        return RoomLookupResponse(room_id="", room_code=room_code.upper(), participant_count=0, exists=False)

    count = db.scalar(select(func.count(Participant.id)).where(Participant.room_id == room.id)) or 0
    return RoomLookupResponse(
        room_id=room.id,
        room_code=room.room_code,
        participant_count=count,
        exists=True,
    )


@router.post("/rooms/{room_code}/join", response_model=RoomResponse)
def join_room(room_code: str, payload: JoinRoomRequest, db: Session = Depends(get_db)) -> RoomResponse:
    service = RoomService(db)
    room = service.get_room(room_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Room does not exist.")

    try:
        participant = service.create_participant(room, payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return RoomResponse(
        room_id=room.id,
        room_code=room.room_code,
        participant_id=participant.id,
        role=participant.role,
    )


@router.get("/rooms/{room_code}/state", response_model=RoomStateResponse)
def room_state(room_code: str, db: Session = Depends(get_db)) -> RoomStateResponse:
    service = RoomService(db)
    room = service.get_room(room_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Room does not exist.")

    return RoomStateResponse(
        room_id=room.id,
        room_code=room.room_code,
        current_video_id=room.current_video_id,
        is_playing=room.is_playing,
        current_time=room.current_time,
        state_updated_at=room.state_updated_at,
        state_version=room.state_version,
    )
