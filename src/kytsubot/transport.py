from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import httpx

from .exceptions import ERROR_BY_STATUS, APIError, InvalidResponse, NetworkError
from .types import DownloadedFile


class AsyncTransport:
    """HTTP transport implementing KytsuBot's JSON envelope."""

    def __init__(
        self,
        base_url: str | Sequence[str],
        *,
        token: str | None = None,
        timeout: float | httpx.Timeout = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        raw_urls = [base_url] if isinstance(base_url, str) else list(base_url)
        self.base_urls = [_normalize_base_url(item) for item in raw_urls]
        if not self.base_urls:
            raise ValueError("at least one API base URL is required")
        self.base_url = self.base_urls[0]
        self.token = token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    def set_token(self, token: str | None) -> None:
        self.token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        files: Mapping[str, Any] | None = None,
        request_timeout: float | httpx.Timeout | None = None,
    ) -> Any:
        request_kwargs: dict[str, Any] = {
            "params": params,
            "json": json_body,
            "files": files,
            "headers": self._headers(),
        }
        if request_timeout is not None:
            request_kwargs["timeout"] = request_timeout
        last_error: httpx.HTTPError | None = None
        response: httpx.Response | None = None
        for base_url in self.base_urls:
            try:
                response = await self._client.request(
                    method,
                    f"{base_url}{path}",
                    **request_kwargs,
                )
                break
            except httpx.HTTPError as exc:
                last_error = exc
        else:
            assert last_error is not None
            raise NetworkError(str(last_error), code="network_error") from last_error
        assert response is not None
        payload = self._decode_json(response)
        if not response.is_success or not payload.get("ok", False):
            error = payload.get("error") or {}
            error_type = ERROR_BY_STATUS.get(response.status_code, APIError)
            raise error_type(
                str(error.get("message", response.reason_phrase or "API request failed")),
                status_code=response.status_code,
                code=str(error.get("code", "api_error")),
                details=payload,
            )
        return payload.get("data")

    async def download(self, path: str) -> DownloadedFile:
        last_error: httpx.HTTPError | None = None
        response: httpx.Response | None = None
        for base_url in self.base_urls:
            try:
                response = await self._client.get(
                    f"{base_url}{path}", headers=self._headers()
                )
                break
            except httpx.HTTPError as exc:
                last_error = exc
        else:
            assert last_error is not None
            raise NetworkError(str(last_error), code="network_error") from last_error
        assert response is not None
        if not response.is_success:
            payload = self._decode_json(response)
            error = payload.get("error") or {}
            error_type = ERROR_BY_STATUS.get(response.status_code, APIError)
            raise error_type(
                str(error.get("message", response.reason_phrase)),
                status_code=response.status_code,
                code=str(error.get("code", "api_error")),
                details=payload,
            )
        return DownloadedFile(
            content=response.content,
            file_name=_content_disposition_filename(response.headers.get("content-disposition")),
            content_type=response.headers.get("content-type"),
        )

    async def upload(self, path: str, source: str | Path | bytes, filename: str | None) -> Any:
        if isinstance(source, bytes):
            actual_name = filename or "upload.bin"
            return await self.request("POST", path, files={"file": (actual_name, source)})
        file_path = Path(source)
        content = await asyncio.to_thread(file_path.read_bytes)
        return await self.request(
            "POST",
            path,
            files={"file": (filename or file_path.name, content)},
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _decode_json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidResponse(
                "server did not return a JSON envelope",
                status_code=response.status_code,
                code="invalid_response",
            ) from exc
        if not isinstance(payload, dict):
            raise InvalidResponse(
                "server returned an invalid JSON envelope",
                status_code=response.status_code,
                code="invalid_response",
            )
        return cast(dict[str, Any], payload)


def _content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    for part in value.split(";")[1:]:
        key, separator, raw = part.strip().partition("=")
        if separator and key.lower() in {"filename", "filename*"}:
            return raw.strip().strip('"')
    return None


def _normalize_base_url(value: str) -> str:
    normalized = value.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    return normalized
