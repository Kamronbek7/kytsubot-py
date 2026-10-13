from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from .bot import Bot
from .router import Router
from .types import Update

logger = logging.getLogger(__name__)

StartupCallback = Callable[[Bot], Awaitable[Any] | Any]


class Dispatcher(Router):
    """Routes updates and manages reliable long polling."""

    def __init__(self, *, name: str | None = None) -> None:
        super().__init__(name=name or "dispatcher")
        self._stop_event = asyncio.Event()
        self._startup: list[StartupCallback] = []
        self._shutdown: list[StartupCallback] = []

    def startup(self, callback: StartupCallback) -> StartupCallback:
        self._startup.append(callback)
        return callback

    def shutdown(self, callback: StartupCallback) -> StartupCallback:
        self._shutdown.append(callback)
        return callback

    async def feed_update(self, bot: Bot, update: Update) -> bool:
        if update.message is not None:
            update.message._bot = bot
            update.message._update_id = update.update_id
        return await self.propagate(update, bot)

    async def start_polling(
        self,
        bot: Bot,
        *,
        consumer_id: str = "default",
        poll_timeout: int = 30,
        limit: int = 100,
        retry_delay: float = 1.0,
        close_bot_session: bool = True,
    ) -> None:
        self._stop_event.clear()
        await self._emit(self._startup, bot)
        try:
            while not self._stop_event.is_set():
                try:
                    batch = await bot.get_updates(
                        consumer_id=consumer_id,
                        limit=limit,
                        timeout=poll_timeout,
                    )
                    for update in batch.updates:
                        try:
                            await self.feed_update(bot, update)
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            handled = await self.propagate_error(exc, update, bot)
                            if not handled:
                                logger.exception(
                                    "KytsuBot update %s failed; it was not acknowledged",
                                    update.update_id,
                                    exc_info=exc,
                                )
                            await asyncio.sleep(retry_delay)
                            break
                        else:
                            await bot.ack_update(update.update_id, consumer_id=consumer_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("KytsuBot polling failed: %s", exc)
                    await asyncio.sleep(retry_delay)
        finally:
            await self._emit(self._shutdown, bot)
            if close_bot_session:
                await bot.close()

    def stop_polling(self) -> None:
        self._stop_event.set()

    def run_polling(self, bot: Bot, **kwargs: Any) -> None:
        with suppress(KeyboardInterrupt):
            asyncio.run(self.start_polling(bot, **kwargs))

    @staticmethod
    async def _emit(callbacks: list[StartupCallback], bot: Bot) -> None:
        for callback in callbacks:
            result = callback(bot)
            if inspect.isawaitable(result):
                await result
