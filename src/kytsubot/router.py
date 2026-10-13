from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .bot import Bot
from .filters import Filter
from .types import Message, Update

HandlerCallback = Callable[..., Awaitable[Any] | Any]


@dataclass(slots=True)
class Handler:
    callback: HandlerCallback
    filters: tuple[Filter, ...] = ()
    flags: dict[str, Any] = field(default_factory=dict)

    async def check(self, event: Any) -> tuple[bool, dict[str, Any]]:
        context: dict[str, Any] = {}
        for event_filter in self.filters:
            result = event_filter(event)
            if inspect.isawaitable(result):
                result = await result
            if not result:
                return False, {}
            if isinstance(result, dict):
                context.update(result)
        return True, context


class EventObserver:
    def __init__(self, event_name: str) -> None:
        self.event_name = event_name
        self.handlers: list[Handler] = []

    def register(
        self,
        callback: HandlerCallback,
        *filters: Filter,
        flags: dict[str, Any] | None = None,
    ) -> HandlerCallback:
        self.handlers.append(Handler(callback, filters, flags or {}))
        return callback

    def __call__(
        self, *filters: Filter, flags: dict[str, Any] | None = None
    ) -> Callable[[HandlerCallback], HandlerCallback]:
        def decorator(callback: HandlerCallback) -> HandlerCallback:
            return self.register(callback, *filters, flags=flags)

        return decorator

    async def trigger(
        self,
        event: Any,
        *,
        bot: Bot,
        update: Update,
        context: dict[str, Any] | None = None,
    ) -> bool:
        for handler in self.handlers:
            matched, filter_data = await handler.check(event)
            if not matched:
                continue
            await _invoke_handler(
                handler.callback,
                event,
                bot=bot,
                update=update,
                context={**(context or {}), **filter_data},
            )
            return True
        return False


class Router:
    def __init__(self, *, name: str | None = None) -> None:
        self.name = name or hex(id(self))
        self.message = EventObserver("message")
        self.update = EventObserver("update")
        self.error = EventObserver("error")
        self.sub_routers: list[Router] = []

    def include_router(self, router: Router) -> Router:
        if router is self:
            raise ValueError("a router cannot include itself")
        self.sub_routers.append(router)
        return router

    def include_routers(self, *routers: Router) -> None:
        for router in routers:
            self.include_router(router)

    async def propagate(self, update: Update, bot: Bot) -> bool:
        if update.message is not None:
            if await self.message.trigger(update.message, bot=bot, update=update):
                return True
        if await self.update.trigger(update, bot=bot, update=update):
            return True
        for router in self.sub_routers:
            if await router.propagate(update, bot):
                return True
        return False

    async def propagate_error(self, error: Exception, update: Update, bot: Bot) -> bool:
        if await self.error.trigger(
            error,
            bot=bot,
            update=update,
            context={"exception": error},
        ):
            return True
        for router in self.sub_routers:
            if await router.propagate_error(error, update, bot):
                return True
        return False


async def _invoke_handler(
    callback: HandlerCallback,
    event: Any,
    *,
    bot: Bot,
    update: Update,
    context: dict[str, Any],
) -> Any:
    signature = inspect.signature(callback)
    parameters = list(signature.parameters.values())
    values: dict[str, Any] = {
        "event": event,
        "message": event if isinstance(event, Message) else update.message,
        "update": update,
        "bot": bot,
        **context,
    }
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    event_used = False
    for parameter in parameters:
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        if parameter.name in values and values[parameter.name] is not None:
            value = values[parameter.name]
            if value is event:
                event_used = True
        elif parameter.default is not parameter.empty:
            continue
        elif not event_used:
            value = event
            event_used = True
        else:
            raise TypeError(f"cannot inject required handler argument: {parameter.name}")
        if parameter.kind is parameter.POSITIONAL_ONLY:
            args.append(value)
        else:
            kwargs[parameter.name] = value
    result = callback(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result
