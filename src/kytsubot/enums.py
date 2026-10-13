from enum import StrEnum


class UserKind(StrEnum):
    GUEST = "guest"
    ACCOUNT = "account"


class Visibility(StrEnum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class AccessPolicy(StrEnum):
    GUEST_ALLOWED = "guest_allowed"
    AUTHENTICATED = "authenticated"
    INVITE_ONLY = "invite_only"


class SenderType(StrEnum):
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"


class UpdateType(StrEnum):
    MESSAGE = "message"

