"""Small HTTP client used only by external collectors."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "innovation-radar/0.1"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_RESPONSE_BYTES = 5_000_000


@dataclass(frozen=True, slots=True)
class HttpJsonResponse:
    """Decoded JSON together with non-sensitive response headers."""

    data: Any
    headers: Mapping[str, str]


class HttpClient:
    """Perform bounded GET requests with no retry or orchestration layer."""

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    def get_bytes(self, url: str, headers: Mapping[str, str] | None = None) -> bytes:
        payload, _ = self._get_bytes_with_headers(url, headers)
        return payload

    def get_json(
        self, url: str, headers: Mapping[str, str] | None = None
    ) -> Any:
        return self.get_json_response(url, headers).data

    def get_json_response(
        self, url: str, headers: Mapping[str, str] | None = None
    ) -> HttpJsonResponse:
        payload, response_headers = self._get_bytes_with_headers(url, headers)
        return HttpJsonResponse(
            data=json.loads(payload.decode("utf-8")),
            headers=response_headers,
        )

    def post_form_json_response(
        self,
        url: str,
        form: Mapping[str, str],
        headers: Mapping[str, str] | None = None,
    ) -> HttpJsonResponse:
        """POST a small form and decode a bounded JSON response."""

        request_headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if headers:
            request_headers.update(headers)
        request = Request(
            url,
            data=urlencode(form).encode("ascii"),
            headers=request_headers,
            method="POST",
        )
        payload, response_headers = self._request_bytes_with_headers(request, url)
        return HttpJsonResponse(
            data=json.loads(payload.decode("utf-8")),
            headers=response_headers,
        )

    def _get_bytes_with_headers(
        self, url: str, headers: Mapping[str, str] | None
    ) -> tuple[bytes, Mapping[str, str]]:
        request_headers = {"User-Agent": USER_AGENT}
        if headers:
            request_headers.update(headers)
        request = Request(url, headers=request_headers)
        return self._request_bytes_with_headers(request, url)

    def _request_bytes_with_headers(
        self, request: Request, url: str
    ) -> tuple[bytes, Mapping[str, str]]:
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = response.read(self.max_response_bytes + 1)
            response_headers = {
                key.lower(): value for key, value in response.headers.items()
            }
        if len(payload) > self.max_response_bytes:
            raise ValueError(
                f"response exceeds {self.max_response_bytes} bytes: {url}"
            )
        return payload, response_headers
