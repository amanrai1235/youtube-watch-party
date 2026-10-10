"""Centralized role-based permissions for Watch Party WebSocket events."""

from app.models.participant import Role


class PermissionDenied(Exception):
    """Raised when a participant tries an action their role cannot perform."""


class PermissionService:
    PLAYBACK_ROLES = {"HOST", "MODERATOR"}

    @staticmethod
    def normalize_role(role) -> str:
        value = getattr(role, "value", role)
        return str(value).strip().upper()

    @classmethod
    def require_playback_control(cls, role: Role) -> None:
        if cls.normalize_role(role) not in cls.PLAYBACK_ROLES:
            raise PermissionDenied("Only the host or a moderator can control playback.")

    @classmethod
    def require_host_or_moderator(cls, role: Role) -> None:
        if cls.normalize_role(role) not in cls.PLAYBACK_ROLES:
            raise PermissionDenied("Only the host or a moderator can perform this action.")

    @classmethod
    def require_host(cls, role: Role) -> None:
        if cls.normalize_role(role) != "HOST":
            raise PermissionDenied("Only the host can perform this action.")
