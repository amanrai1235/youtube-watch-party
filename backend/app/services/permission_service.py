
from app.models.participant import Role


class PermissionDenied(Exception):
    """Raised when a participant cannot perform an action."""


class PermissionService:
    PLAYBACK_ROLES = {"HOST", "MODERATOR"}

    @staticmethod
    def _normalize_role(role) -> str:
        alue = getattr(role, "value", role)
        return str(value).strip().upper()

    @classmethod
    def require_playback_control(cls, role: Role) -> None:
        """Host and Moderator can control playback."""
        if cls._normalize_role(role) not in cls.PLAYBACK_ROLES:
            raise PermissionDenied(
                "Only the host or a moderator can control playback."
            )

    @classmethod
    def require_host_or_moderator(cls, role: Role) -> None:
        """Host and Moderator can resolve participant requests."""
        if cls._normalize_role(role) not in cls.PLAYBACK_ROLES:
            raise PermissionDenied(
                "Only the host or a moderator can perform this action."
            )

    @classmethod
    def require_host(cls, role: Role) -> None:
        """Keep host-only operations restricted to the Host."""
        if cls._normalize_role(role) != "HOST":
            raise PermissionDenied(
                "Only the host can perform this action."
            )
