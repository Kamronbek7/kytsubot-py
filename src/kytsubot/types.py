from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .enums import AccessPolicy, SenderType, UpdateType, UserKind, Visibility

if TYPE_CHECKING:
    from .bot import Bot


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(slots=True)
class User:
    id: str
    kind: UserKind
    status: str
    email: str | None = None
    username: str | None = None
    display_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> User:
        return cls(
            id=str(data["id"]),
            kind=UserKind(data["kind"]),
            status=str(data.get("status", "active")),
            email=data.get("email"),
            username=data.get("username"),
            display_name=data.get("display_name"),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


@dataclass(slots=True)
class BotInfo:
    id: str
    display_name: str
    description: str
    visibility: Visibility
    access_policy: AccessPolicy
    status: str
    username: str | None = None
    last_activity_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BotInfo:
        return cls(
            id=str(data["id"]),
            display_name=str(data.get("display_name", "")),
            description=str(data.get("description", "")),
            visibility=Visibility(data.get("visibility", Visibility.PRIVATE)),
            access_policy=AccessPolicy(data.get("access_policy", AccessPolicy.GUEST_ALLOWED)),
            status=str(data.get("status", "active")),
            username=data.get("username"),
            last_activity_at=parse_datetime(data.get("last_activity_at")),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


@dataclass(slots=True)
class Chat:
    chat_id: str
    bot_id: str
    bot_user_id: str
    status: str
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    last_activity_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Chat:
        return cls(
            chat_id=str(data["chat_id"]),
            bot_id=str(data["bot_id"]),
            bot_user_id=str(data["bot_user_id"]),
            status=str(data["status"]),
            started_at=parse_datetime(data.get("started_at")),
            stopped_at=parse_datetime(data.get("stopped_at")),
            last_activity_at=parse_datetime(data.get("last_activity_at")),
        )


@dataclass(slots=True)
class File:
    file_id: str
    file_name: str
    mime_type: str
    size: int
    scan_status: str
    expires_at: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> File:
        return cls(
            file_id=str(data["file_id"]),
            file_name=str(data.get("file_name", "")),
            mime_type=str(data.get("mime_type", "application/octet-stream")),
            size=int(data.get("size", 0)),
            scan_status=str(data.get("scan_status", "pending")),
            expires_at=parse_datetime(data.get("expires_at")),
            created_at=parse_datetime(data.get("created_at")),
        )


@dataclass(slots=True)
class DownloadedFile:
    content: bytes
    file_name: str | None
    content_type: str | None

    def save(self, destination: str | Path) -> Path:
        path = Path(destination)
        if path.is_dir() and self.file_name:
            path = path / self.file_name
        path.write_bytes(self.content)
        return path


@dataclass(slots=True)
class Message:
    message_id: str
    chat_id: str
    sender_type: SenderType
    attachments: list[File] = field(default_factory=list)
    text: str | None = None
    sender_user_id: str | None = None
    created_at: datetime | None = None
    _bot: Bot | None = field(default=None, repr=False, compare=False)
    _update_id: int | None = field(default=None, repr=False, compare=False)
    _reply_index: int = field(default=0, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Message:
        return cls(
            message_id=str(data["message_id"]),
            chat_id=str(data["chat_id"]),
            sender_type=SenderType(data["sender_type"]),
            attachments=[File.from_dict(item) for item in data.get("attachments") or []],
            text=data.get("text"),
            sender_user_id=data.get("sender_user_id"),
            created_at=parse_datetime(data.get("created_at")),
        )

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            raise RuntimeError("Message is not bound to a Bot")
        return self._bot

    async def answer(
        self,
        text: str | None = None,
        *,
        attachments: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Message:
        generated_key = False
        if idempotency_key is None and self._update_id is not None:
            idempotency_key = f"update:{self._update_id}:reply:{self._reply_index}"
            generated_key = True
        result = await self.bot.send_message(
            self.chat_id,
            text,
            attachments=attachments,
            idempotency_key=idempotency_key,
        )
        if generated_key:
            self._reply_index += 1
        return result

    reply = answer


@dataclass(slots=True)
class Update:
    update_id: int
    type: UpdateType | str
    payload: dict[str, Any]
    created_at: datetime | None = None
    message: Message | None = None
    user: User | None = None
    chat_id: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Update:
        payload: dict[str, Any] = dict(data.get("payload") or {})
        raw_message = payload.get("message")
        raw_user = payload.get("user")
        try:
            update_type: UpdateType | str = UpdateType(data["type"])
        except ValueError:
            update_type = str(data["type"])
        return cls(
            update_id=int(data["update_id"]),
            type=update_type,
            payload=payload,
            created_at=parse_datetime(data.get("created_at")),
            message=Message.from_dict(raw_message) if isinstance(raw_message, Mapping) else None,
            user=User.from_dict(raw_user) if isinstance(raw_user, Mapping) else None,
            chat_id=payload.get("chat_id"),
        )


@dataclass(slots=True)
class UpdateBatch:
    updates: list[Update]
    consumer_id: str
    next_offset: int


@dataclass(slots=True)
class AuthResult:
    user: User
    session_token: str


@dataclass(slots=True)
class CreatedBot:
    bot: BotInfo
    bot_token: str
    token_notice: str


@dataclass(slots=True)
class StartedBot:
    chat: Chat
    message: Message


@dataclass(slots=True)
class AckResult:
    consumer_id: str
    last_acked_update_id: int
