from __future__ import annotations

from typing import Any

import pytest

from kytsubot import AckResult, Bot, Command, Dispatcher, Message, Router, Update, UpdateBatch


@pytest.mark.asyncio
async def test_dispatcher_routes_message_and_injects_command() -> None:
    router = Router()
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    called: dict[str, Any] = {}

    @router.message(Command("start"))
    async def start(message: Message, command: Any) -> None:
        called["text"] = message.text
        called["args"] = command.args

    update = Update.from_dict(
        {
            "update_id": 10,
            "type": "message",
            "payload": {
                "chat_id": "cht_1",
                "user": {"id": "bu_1", "kind": "guest", "status": "active"},
                "message": {
                    "message_id": "msg_1",
                    "chat_id": "cht_1",
                    "sender_type": "user",
                    "text": "/start demo",
                    "attachments": [],
                },
            },
        }
    )
    bot = Bot("kb_live.test", base_url="https://test.invalid")
    assert await dispatcher.feed_update(bot, update)
    assert called == {"text": "/start demo", "args": "demo"}
    await bot.close()


@pytest.mark.asyncio
async def test_polling_acknowledges_only_after_success() -> None:
    dispatcher = Dispatcher()
    acknowledgements: list[int] = []
    update = Update.from_dict(
        {
            "update_id": 11,
            "type": "message",
            "payload": {
                "chat_id": "cht_1",
                "message": {
                    "message_id": "msg_2",
                    "chat_id": "cht_1",
                    "sender_type": "user",
                    "text": "done",
                    "attachments": [],
                },
            },
        }
    )

    @dispatcher.message()
    async def consume(message: Message) -> None:
        assert message.text == "done"
        dispatcher.stop_polling()

    class FakeBot:
        async def get_updates(self, **_: Any) -> UpdateBatch:
            return UpdateBatch([update], "worker", 12)

        async def ack_update(self, update_id: int, **_: Any) -> AckResult:
            acknowledgements.append(update_id)
            return AckResult("worker", update_id)

        async def close(self) -> None:
            return None

    await dispatcher.start_polling(FakeBot(), consumer_id="worker")  # type: ignore[arg-type]
    assert acknowledgements == [11]
