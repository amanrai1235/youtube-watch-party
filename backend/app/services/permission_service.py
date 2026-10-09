from app.models.participant import Role


class PermissionDenied(Exception):
    pass


class PermissionService:
    PLAYBACK_ROLES = {Role.HOST, Role.MODERATOR}

    @classmethod
    def require_playback_control(cls, role: Role) -> None:
        if role not in cls.PLAYBACK_ROLES:
            raise PermissionDenied("Only the host or moderator can control playback.")

    @classmethod
    def require_host(cls, role: Role) -> None:
        if role != Role.HOST:
            raise PermissionDenied("Only the host can perform this action.")
