from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .exceptions import ClientError
from .transport import AsyncTransport
from .types import AckResult, DownloadedFile, File, Message, Update, UpdateBatch

PRODUCTION_BOT_API = "https://bot.inviprog.uz"
LEGACY_BOT_API = "https://bot.kytsubot.uz"
TEST_BOT_API = "http://127.0.0.1:8081"


class Bot:
    """Asynchronous KytsuBot Bot API client."""

    def __init__(
        self,
        token: str,
        *,
        test_mode: bool = False,
        base_url: str | None = None,
        fallback_base_urls: list[str] | None = None,
        timeout: float | httpx.Timeout = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not token or not token.strip():
            raise ClientError("bot token must not be empty")
        if base_url is not None:
            resolved_urls = [base_url, *(fallback_base_urls or [])]
        elif test_mode:
            resolved_urls = [TEST_BOT_API]
        else:
            resolved_urls = [PRODUCTION_BOT_API, LEGACY_BOT_API]
        self.token = token.strip()
        self.test_mode = test_mode
        self.transport = AsyncTransport(
            resolved_urls, token=self.token, timeout=timeout, client=http_client
        )

    async def get_updates(
        self,
        *,
        consumer_id: str = "default",
        offset: int | None = None,
        limit: int = 100,
        timeout: int = 30,  # noqa: ASYNC109 - server long-poll wait, not coroutine deadline
    ) -> UpdateBatch:
        params: dict[str, Any] = {
            "consumer_id": consumer_id,
            "limit": limit,
            "timeout": timeout,
        }
        if offset is not None:
            params["offset"] = offset
        data = await self.transport.request(
            "GET",
            "/v1/bot/updates",
            params=params,
            request_timeout=float(timeout + 10),
        )
        return UpdateBatch(
            updates=[Update.from_dict(item) for item in data.get("updates") or []],
            consumer_id=str(data.get("consumer_id", consumer_id)),
            next_offset=int(data.get("next_offset", offset or 0)),
        )

    async def health(self) -> dict[str, Any]:
        data = await self.transport.request("GET", "/healthz")
        return dict(data)

    async def ack_update(self, update_id: int, *, consumer_id: str = "default") -> AckResult:
        data = await self.transport.request(
            "POST",
            "/v1/bot/updates/ack",
            json_body={"consumer_id": consumer_id, "update_id": update_id},
        )
        return AckResult(
            consumer_id=str(data["consumer_id"]),
            last_acked_update_id=int(data["last_acked_update_id"]),
        )

    async def send_message(
        self,
        chat_id: str,
        text: str | None = None,
        *,
        attachments: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Message:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "attachments": attachments or [],
        }
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        data = await self.transport.request("POST", "/v1/bot/messages", json_body=payload)
        message = Message.from_dict(data)
        message._bot = self
        return message

    async def upload_file(
        self, source: str | Path | bytes, *, filename: str | None = None
    ) -> File:
        data = await self.transport.upload("/v1/files", source, filename)
        return File.from_dict(data)

    async def download_file(self, file_id: str) -> DownloadedFile:
        return await self.transport.download(f"/v1/files/{quote(file_id, safe='')}")

    async def close(self) -> None:
        await self.transport.close()

    async def __aenter__(self) -> Bot:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
