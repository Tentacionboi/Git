"""Minimal API-Football client helpers for source probing."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
API_FOOTBALL_KEY_ENV_VAR = "API_FOOTBALL_KEY"


UrlOpener = Callable[..., Any]


@dataclass(frozen=True)
class ApiFootballRequestError(Exception):
    """Sanitized API-Football request failure."""

    message: str
    status_code: int | None = None
    response_body: str = ""

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.response_body:
            parts.append(f"response_body={self.response_body}")
        return "; ".join(parts)


def get_api_football_key_from_env(
    *,
    env_var: str = API_FOOTBALL_KEY_ENV_VAR,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Read an API-Football key from the environment."""
    source = environ if environ is not None else os.environ
    value = source.get(env_var, "").strip()
    if not value:
        raise ValueError(f"{env_var} is not set")
    return value


def build_api_football_url(
    endpoint: str,
    *,
    params: Mapping[str, Any] | None = None,
    base_url: str = API_FOOTBALL_BASE_URL,
) -> str:
    """Build an API-Football URL from an endpoint and query parameters."""
    clean_endpoint = endpoint.strip()
    if not clean_endpoint:
        raise ValueError("endpoint cannot be empty")
    if not clean_endpoint.startswith("/"):
        clean_endpoint = f"/{clean_endpoint}"
    query_params = {
        key: value
        for key, value in (params or {}).items()
        if value is not None and str(value).strip()
    }
    query = urlencode(query_params)
    if query:
        return f"{base_url}{clean_endpoint}?{query}"
    return f"{base_url}{clean_endpoint}"


def fetch_api_football_payload(
    *,
    api_key: str,
    endpoint: str,
    params: Mapping[str, Any] | None = None,
    timeout_seconds: float = 30.0,
    opener: UrlOpener | None = None,
) -> dict[str, Any]:
    """Fetch one JSON payload from API-Football."""
    url = build_api_football_url(endpoint, params=params)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "x-apisports-key": api_key,
        },
    )
    open_url = opener or urlopen
    try:
        with open_url(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ApiFootballRequestError(
            "API-Football request failed",
            status_code=exc.code,
            response_body=_read_error_body(exc),
        ) from exc
    except URLError as exc:
        raise ApiFootballRequestError(f"API-Football network error: {exc.reason}") from exc
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("API-Football response must be a JSON object")
    return payload


def _read_error_body(exc: HTTPError) -> str:
    try:
        return exc.read().decode("utf-8")[:1000]
    except Exception:
        return ""
