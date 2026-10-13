from __future__ import annotations

import json

import httpx
import pytest

from kytsubot import Bot


@pytest.mark.asyncio
async def test_bot_parses_updates_and_sends_idempotent_answer() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/bot/updates":
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "data": {
                        "consumer_id": "test",
                        "next_offset": 8,
                        "updates": [
                            {
                                "update_id": 7,
                                "type": "message",
                                "payload": {
                                    "chat_id": "cht_1",
                                    "user": {"id": "bu_1", "kind": "guest", "status": "active"},
                                    "message": {
                                        "message_id": "msg_1",
                                        "chat_id": "cht_1",
                                        "sender_type": "user",
                                        "text": "ping",
                                        "attachments": [],
                                    },
                                },
                            }
                        ],
                    },
                },
            )
        if request.url.path == "/v1/bot/messages":
            payload = json.loads(request.content)
            assert payload["idempotency_key"] == "update:7:reply:0"
            return httpx.Response(
                201,
                json={
                    "ok": True,
                    "data": {
                        "message_id": "msg_2",
                        "chat_id": "cht_1",
                        "sender_type": "bot",
                        "text": "pong",
                        "attachments": [],
                    },
                },
            )
        raise AssertionError(request.url)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    bot = Bot("kb_live.test", base_url="https://test.invalid", http_client=client)
    batch = await bot.get_updates(consumer_id="test", timeout=0)
    update = batch.updates[0]
    assert update.message is not None
    update.message._bot = bot
    update.message._update_id = update.update_id
    response = await update.message.answer("pong")
    assert response.message_id == "msg_2"
    assert requests[0].headers["authorization"] == "Bearer kb_live.test"
    await client.aclose()


@pytest.mark.asyncio
async def test_production_falls_back_only_after_network_error() -> None:
    hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        if request.url.host == "bot.inviprog.uz":
            raise httpx.ConnectError("primary unavailable", request=request)
        return httpx.Response(200, json={"ok": True, "data": {"status": "ok"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    bot = Bot("kb_live.test", http_client=client)
    assert await bot.health() == {"status": "ok"}
    assert hosts == ["bot.inviprog.uz", "bot.kytsubot.uz"]
    await client.aclose()
