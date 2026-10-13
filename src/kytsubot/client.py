from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .enums import AccessPolicy, Visibility
from .transport import AsyncTransport
from .types import (
    AuthResult,
    BotInfo,
    Chat,
    CreatedBot,
    DownloadedFile,
    File,
    Message,
    StartedBot,
    User,
)

PRODUCTION_USER_API = "https://kytsubot.inviprog.uz"
LEGACY_USER_API = "https://kytsubot.uz"
TEST_USER_API = "http://127.0.0.1:8080"


def _bot_ref(value: str) -> str:
    return quote(value.strip().removeprefix("@"), safe="")


class KytsuClient:
    """Account, bot management and user chat API client."""

    def __init__(
        self,
        session_token: str | None = None,
        *,
        test_mode: bool = False,
        base_url: str | None = None,
        fallback_base_urls: list[str] | None = None,
        timeout: float | httpx.Timeout = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if base_url is not None:
            resolved_urls = [base_url, *(fallback_base_urls or [])]
        elif test_mode:
            resolved_urls = [TEST_USER_API]
        else:
            resolved_urls = [PRODUCTION_USER_API, LEGACY_USER_API]
        self.session_token = session_token
        self.test_mode = test_mode
        self.transport = AsyncTransport(
            resolved_urls, token=session_token, timeout=timeout, client=http_client
        )

    def set_session_token(self, token: str | None) -> None:
        self.session_token = token
        self.transport.set_token(token)

    async def health(self) -> dict[str, Any]:
        data = await self.transport.request("GET", "/healthz")
        return dict(data)

    async def create_guest(self) -> AuthResult:
        return self._apply_auth(await self.transport.request("POST", "/v1/auth/guest", json_body={}))

    async def register(
        self, email: str, password: str, *, display_name: str | None = None
    ) -> AuthResult:
        payload = {"email": email, "password": password}
        if display_name is not None:
            payload["display_name"] = display_name
        return self._apply_auth(
            await self.transport.request("POST", "/v1/auth/register", json_body=payload)
        )

    async def login(self, email: str, password: str) -> AuthResult:
        return self._apply_auth(
            await self.transport.request(
                "POST", "/v1/auth/login", json_body={"email": email, "password": password}
            )
        )

    def _apply_auth(self, data: dict[str, Any]) -> AuthResult:
        result = AuthResult(user=User.from_dict(data["user"]), session_token=data["session_token"])
        self.set_session_token(result.session_token)
        return result

    async def get_me(self) -> User:
        return User.from_dict(await self.transport.request("GET", "/v1/me"))

    async def list_owned_bots(self) -> list[BotInfo]:
        data = await self.transport.request("GET", "/v1/me/bots")
        return [BotInfo.from_dict(item) for item in data.get("bots") or []]

    async def list_bots(self, *, limit: int = 20, offset: int = 0) -> list[BotInfo]:
        data = await self.transport.request(
            "GET", "/v1/bots", params={"limit": limit, "offset": offset}
        )
        return [BotInfo.from_dict(item) for item in data.get("bots") or []]

    async def get_bot(self, bot: str) -> BotInfo:
        return BotInfo.from_dict(
            await self.transport.request("GET", f"/v1/bots/{_bot_ref(bot)}")
        )

    async def create_bot(
        self,
        display_name: str,
        *,
        username: str | None = None,
        description: str = "",
        visibility: Visibility | str = Visibility.PRIVATE,
        access_policy: AccessPolicy | str = AccessPolicy.GUEST_ALLOWED,
    ) -> CreatedBot:
        data = await self.transport.request(
            "POST",
            "/v1/bots",
            json_body={
                "username": username,
                "display_name": display_name,
                "description": description,
                "visibility": str(visibility),
                "access_policy": str(access_policy),
            },
        )
        return CreatedBot(
            bot=BotInfo.from_dict(data["bot"]),
            bot_token=str(data["bot_token"]),
            token_notice=str(data.get("token_notice", "")),
        )

    async def update_bot(
        self,
        bot: str,
        *,
        display_name: str,
        username: str | None,
        description: str,
        visibility: Visibility | str,
        access_policy: AccessPolicy | str,
    ) -> BotInfo:
        data = await self.transport.request(
            "PUT",
            f"/v1/bots/{_bot_ref(bot)}/settings",
            json_body={
                "username": username,
                "display_name": display_name,
                "description": description,
                "visibility": str(visibility),
                "access_policy": str(access_policy),
            },
        )
        return BotInfo.from_dict(data)

    async def delete_bot(self, bot: str) -> bool:
        data = await self.transport.request("DELETE", f"/v1/bots/{_bot_ref(bot)}")
        return bool(data.get("deleted"))

    async def rotate_bot_token(self, bot: str) -> str:
        data = await self.transport.request(
            "POST", f"/v1/bots/{_bot_ref(bot)}/tokens/rotate", json_body={}
        )
        return str(data["bot_token"])

    async def start_bot(self, bot: str, *, payload: str = "") -> StartedBot:
        data = await self.transport.request(
            "POST", f"/v1/bots/{_bot_ref(bot)}/start", json_body={"payload": payload}
        )
        return StartedBot(
            chat=Chat.from_dict(data["chat"]),
            message=Message.from_dict(data["message"]),
        )

    async def stop_bot(self, bot: str) -> bool:
        data = await self.transport.request(
            "POST", f"/v1/bots/{_bot_ref(bot)}/stop", json_body={}
        )
        return bool(data.get("stopped"))

    async def list_messages(self, bot: str, *, limit: int = 50) -> list[Message]:
        data = await self.transport.request(
            "GET", f"/v1/bots/{_bot_ref(bot)}/messages", params={"limit": limit}
        )
        return [Message.from_dict(item) for item in data.get("messages") or []]

    async def send_message(
        self,
        bot: str,
        text: str | None = None,
        *,
        attachments: list[str] | None = None,
    ) -> Message:
        data = await self.transport.request(
            "POST",
            f"/v1/bots/{_bot_ref(bot)}/messages",
            json_body={"text": text, "attachments": attachments or []},
        )
        return Message.from_dict(data)

    async def upload_file(
        self, source: str | Path | bytes, *, filename: str | None = None
    ) -> File:
        return File.from_dict(await self.transport.upload("/v1/files", source, filename))

    async def download_file(self, file_id: str) -> DownloadedFile:
        return await self.transport.download(f"/v1/files/{quote(file_id, safe='')}")

    async def close(self) -> None:
        await self.transport.close()

    async def __aenter__(self) -> KytsuClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
