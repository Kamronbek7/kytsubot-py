from __future__ import annotations

from typing import Any


class KytsuBotError(Exception):
    """Base exception for the SDK."""


class ClientError(KytsuBotError):
    """Invalid local argument or client state."""


class APIError(KytsuBotError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str = "api_error",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.details = details

    def __str__(self) -> str:
        status = f" [{self.status_code}]" if self.status_code is not None else ""
        return f"{self.code}{status}: {super().__str__()}"


class NetworkError(APIError):
    pass


class Unauthorized(APIError):
    pass


class Forbidden(APIError):
    pass


class NotFound(APIError):
    pass


class Conflict(APIError):
    pass


class RateLimited(APIError):
    pass


class ServerUnavailable(APIError):
    pass


class InvalidResponse(APIError):
    pass


ERROR_BY_STATUS: dict[int, type[APIError]] = {
    401: Unauthorized,
    403: Forbidden,
    404: NotFound,
    409: Conflict,
    429: RateLimited,
    502: ServerUnavailable,
    503: ServerUnavailable,
    504: ServerUnavailable,
}

