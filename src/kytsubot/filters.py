from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .types import Message

FilterResult = bool | dict[str, Any]
FilterReturn = FilterResult | Awaitable[FilterResult]


class Filter(Protocol):
    def __call__(self, event: Any) -> FilterReturn: ...


def _resolve(value: Any, path: tuple[str, ...]) -> Any:
    for name in path:
        if value is None:
            return None
        if isinstance(value, Mapping):
            value = value.get(name)
        else:
            value = getattr(value, name, None)
    return value


class MagicFilter:
    """A compact aiogram-style field expression used through the global ``F`` object."""

    def __init__(
        self,
        path: tuple[str, ...] = (),
        transforms: tuple[Callable[[Any], Any], ...] = (),
        predicate: Callable[[Any], bool] | None = None,
    ) -> None:
        self._path = path
        self._transforms = transforms
        self._predicate = predicate

    def __getattr__(self, name: str) -> MagicFilter:
        if name.startswith("_"):
            raise AttributeError(name)
        return MagicFilter(self._path + (name,), self._transforms)

    def _value(self, event: Any) -> Any:
        value = _resolve(event, self._path)
        for transform in self._transforms:
            if value is None:
                return None
            value = transform(value)
        return value

    def _compare(self, operation: Callable[[Any], bool]) -> MagicFilter:
        return MagicFilter(self._path, self._transforms, operation)

    def __call__(self, event: Any) -> bool:
        value = self._value(event)
        return bool(self._predicate(value) if self._predicate else value)

    def __eq__(self, other: object) -> MagicFilter:  # type: ignore[override]
        return self._compare(lambda value: value == other)

    def __ne__(self, other: object) -> MagicFilter:  # type: ignore[override]
        return self._compare(lambda value: value != other)

    def __contains__(self, item: object) -> bool:
        raise TypeError("Use F.field.contains(value), not 'value in F.field'")

    def contains(self, value: object) -> MagicFilter:
        return self._compare(lambda actual: actual is not None and value in actual)

    def startswith(self, value: str) -> MagicFilter:
        return self._compare(
            lambda actual: isinstance(actual, str) and actual.startswith(value)
        )

    def endswith(self, value: str) -> MagicFilter:
        return self._compare(lambda actual: isinstance(actual, str) and actual.endswith(value))

    def regexp(self, pattern: str | re.Pattern[str]) -> MagicFilter:
        expression = re.compile(pattern) if isinstance(pattern, str) else pattern
        return self._compare(
            lambda actual: isinstance(actual, str) and expression.search(actual) is not None
        )

    def in_(self, values: object) -> MagicFilter:
        return self._compare(lambda actual: actual in values)  # type: ignore[operator]

    def casefold(self) -> MagicFilter:
        return MagicFilter(self._path, self._transforms + (str.casefold,))

    def lower(self) -> MagicFilter:
        return MagicFilter(self._path, self._transforms + (str.lower,))

    def __and__(self, other: MagicFilter) -> MagicFilter:
        return MagicFilter(predicate=lambda event: bool(self(event)) and bool(other(event)))

    def __or__(self, other: MagicFilter) -> MagicFilter:
        return MagicFilter(predicate=lambda event: bool(self(event)) or bool(other(event)))

    def __invert__(self) -> MagicFilter:
        return MagicFilter(predicate=lambda event: not self(event))


F = MagicFilter()


@dataclass(slots=True, frozen=True)
class CommandObject:
    prefix: str
    command: str
    mention: str | None
    args: str | None


class Command:
    def __init__(self, *commands: str, prefix: str = "/", ignore_case: bool = True) -> None:
        if not commands:
            raise ValueError("at least one command is required")
        self.commands = {item.removeprefix(prefix) for item in commands}
        self.prefix = prefix
        self.ignore_case = ignore_case

    def __call__(self, event: Any) -> FilterResult:
        if not isinstance(event, Message) or not event.text:
            return False
        head, _, raw_args = event.text.strip().partition(" ")
        if not head.startswith(self.prefix):
            return False
        name, separator, mention = head[len(self.prefix) :].partition("@")
        expected = {value.casefold() for value in self.commands} if self.ignore_case else self.commands
        actual = name.casefold() if self.ignore_case else name
        if actual not in expected:
            return False
        return {
            "command": CommandObject(
                prefix=self.prefix,
                command=name,
                mention=mention if separator else None,
                args=raw_args.strip() or None,
            )
        }


class Keyword:
    def __init__(self, *words: str, contains: bool = False, ignore_case: bool = True) -> None:
        if not words:
            raise ValueError("at least one keyword is required")
        self.words = words
        self.contains_mode = contains
        self.ignore_case = ignore_case

    def __call__(self, event: Any) -> bool:
        if not isinstance(event, Message) or event.text is None:
            return False
        text = event.text.casefold() if self.ignore_case else event.text
        words = (word.casefold() for word in self.words) if self.ignore_case else self.words
        if self.contains_mode:
            return any(word in text for word in words)
        return any(word == text for word in words)
