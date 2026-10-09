
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.participant import Participant, Role
from app.models.room import Room


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoomService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_room_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits

        for _ in range(10):
            code = "".join(
                secrets.choice(alphabet)
                for _ in range(settings.room_code_length)
            )

            existing_room = self.db.scalar(
                select(Room).where(Room.room_code == code)
            )

            if existing_room is None:
                return code

        raise RuntimeError("Unable to generate a unique room code")

    def create_room(self, username: str) -> tuple[Room, Participant]:
        username = username.strip()

        if not username:
            raise ValueError("Username cannot be empty.")

        room = Room(room_code=self._generate_room_code())

        participant = Participant(
            username=username,
            role=Role.HOST,
            online=False,
        )

        room.participants.append(participant)

        self.db.add(room)
        self.db.flush()

        room.host_participant_id = participant.id

        self.db.commit()
        self.db.refresh(room)
        self.db.refresh(participant)

        return room, participant

    def get_room(self, room_code: str) -> Room | None:
        return self.db.scalar(
            select(Room).where(
                Room.room_code == room_code.strip().upper()
            )
        )

    def get_participant(
        self,
        participant_id: str,
        room_id: str | None = None,
    ) -> Participant | None:
        query = select(Participant).where(
            Participant.id == participant_id
        )

        if room_id:
            query = query.where(
                Participant.room_id == room_id
            )

        return self.db.scalar(query)

    def create_participant(
        self,
        room: Room,
        username: str,
    ) -> Participant:
        username = username.strip()

        if not username:
            raise ValueError("Username cannot be empty.")

        existing = self.db.scalar(
            select(Participant).where(
                Participant.room_id == room.id,
                Participant.username.ilike(username),
            )
        )

        if existing is not None:
            if existing.online:
                raise ValueError(
                    "This username is already online in this room."
                )

            # Reuse the offline participant instead of creating
            # a new record. Preserve their existing role and ID.
            existing.online = False
            existing.last_seen = utc_now()

            self.db.commit()
            self.db.refresh(existing)

            return existing

        participant = Participant(
            room_id=room.id,
            username=username,
            role=Role.PARTICIPANT,
            online=False,
        )

        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)

        return participant

    def mark_online(
        self,
        participant: Participant,
        online: bool,
    ) -> None:
        participant.online = online
        participant.last_seen = utc_now()

        self.db.commit()
