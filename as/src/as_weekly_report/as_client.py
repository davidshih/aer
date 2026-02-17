"""Adaptive Shield API client."""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any, Callable, Deque
from urllib.parse import parse_qs, urlparse

import requests

logger = logging.getLogger(__name__)


class AdaptiveShieldClientError(RuntimeError):
    """Base exception for Adaptive Shield client failures."""


class AuthenticationError(AdaptiveShieldClientError):
    """Raised when API key is invalid or missing required permissions."""


class ApiRequestError(AdaptiveShieldClientError):
    """Raised when request retries are exhausted."""


class AdaptiveShieldClient:
    """Client for Adaptive Shield REST API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.adaptive-shield.com",
        *,
        rate_limit_per_minute: int = 90,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        session: requests.Session | None = None,
        sleep_func: Callable[[float], None] = time.sleep,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        if not api_key:
            raise ValueError("AS_API_KEY is required")

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.rate_limit_per_minute = rate_limit_per_minute
        self._sleep = sleep_func
        self._time = time_func
        self._request_times: Deque[float] = deque()
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json",
            }
        )

    def get_accounts(self) -> list[dict[str, Any]]:
        """List account IDs available to the current API key."""
        records = self._paginate("GET", "/api/v1/accounts")
        return [item for item in records if isinstance(item, dict)]

    def get_alerts(
        self,
        account_id: str,
        from_date: str,
        to_date: str,
        alert_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch alerts for an account and optional type."""
        path = f"/api/v1/accounts/{account_id}/alerts"
        params: dict[str, Any] = {"from_date": from_date, "to_date": to_date}
        if alert_type:
            params["type"] = alert_type
        records = self._paginate("GET", path, params=params)
        return [item for item in records if isinstance(item, dict)]

    def get_security_check(
        self,
        account_id: str,
        security_check_id: str,
    ) -> dict[str, Any]:
        """Fetch security check details by ID."""
        path = (
            f"/api/v1/accounts/{account_id}/security_checks/{security_check_id}"
        )
        payload = self._request("GET", path)
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]
        if isinstance(payload, dict):
            return payload
        return {}

    def get_affected_entities(
        self,
        account_id: str,
        security_check_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch affected entities for a non-global security check."""
        path = (
            f"/api/v1/accounts/{account_id}/security_checks/"
            f"{security_check_id}/affected"
        )
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        records = self._paginate("GET", path, params=params)
        return [item for item in records if isinstance(item, dict)]

    def get_integrations(self, account_id: str) -> list[dict[str, Any]]:
        """List integrations for an account."""
        path = f"/api/v1/accounts/{account_id}/integrations"
        records = self._paginate("GET", path)
        return [item for item in records if isinstance(item, dict)]

    def get_security_checks_by_account(
        self,
        account_id: str,
    ) -> list[dict[str, Any]]:
        """List security checks for an account."""
        path = f"/api/v1/accounts/{account_id}/security_checks"
        records = self._paginate("GET", path)
        return [item for item in records if isinstance(item, dict)]

    def get_security_checks_by_integration(
        self,
        account_id: str,
        integration_id: str,
    ) -> list[dict[str, Any]]:
        """List security checks for a specific integration."""
        path = (
            f"/api/v1/accounts/{account_id}/integrations/"
            f"{integration_id}/security_checks"
        )
        records = self._paginate("GET", path)
        return [item for item in records if isinstance(item, dict)]

    def _paginate(
        self,
        method: str,
        path_or_url: str,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Fetch every page from endpoints that expose next URI or meta pagination."""
        all_items: list[Any] = []
        seen_ids: set[str] = set()
        seen_pages: set[tuple[str, tuple[tuple[str, str], ...]]] = set()

        original_path = path_or_url
        next_path = path_or_url
        next_params = dict(params or {})

        while True:
            page_key = (
                next_path,
                tuple(
                    sorted(
                        (str(k), str(v))
                        for k, v in (next_params or {}).items()
                    )
                ),
            )
            if page_key in seen_pages:
                logger.warning("Pagination loop detected for %s", next_path)
                break
            seen_pages.add(page_key)

            payload = self._request(method, next_path, params=next_params or None)
            items, next_page_uri, pagination = self._extract_page(payload)

            for item in items:
                if isinstance(item, dict) and item.get("id") is not None:
                    item_id = str(item["id"])
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                all_items.append(item)

            if next_page_uri:
                next_path = next_page_uri
                next_params = {}
                continue

            next_from_meta = self._next_from_meta(
                original_path=original_path,
                current_params=next_params,
                pagination=pagination,
            )
            if next_from_meta is None:
                break

            next_path, next_params = next_from_meta

        return all_items

    def _request(
        self,
        method: str,
        path_or_url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Run one request with retry and throttling."""
        url = self._resolve_url(path_or_url)
        attempt = 0

        while True:
            self._throttle()
            try:
                response = self._session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                if attempt >= self.max_retries:
                    raise ApiRequestError(
                        f"Request failed after retries: {method} {url}"
                    ) from exc
                wait_seconds = float(2**attempt)
                logger.warning(
                    "Request error on %s %s, retrying in %.1fs: %s",
                    method,
                    url,
                    wait_seconds,
                    exc,
                )
                self._sleep(wait_seconds)
                attempt += 1
                continue

            if response.status_code == 401:
                raise AuthenticationError(
                    "Unauthorized (401). Verify AS_API_KEY and account access."
                )

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = self._parse_retry_after(
                    response.headers.get("Retry-After")
                )
                wait_seconds = retry_after if retry_after is not None else float(2**attempt)
                logger.warning(
                    "Rate limited on %s %s, retrying in %.1fs",
                    method,
                    url,
                    wait_seconds,
                )
                self._sleep(wait_seconds)
                attempt += 1
                continue

            if 500 <= response.status_code < 600 and attempt < self.max_retries:
                wait_seconds = float(2**attempt)
                logger.warning(
                    "Server error %s on %s %s, retrying in %.1fs",
                    response.status_code,
                    method,
                    url,
                    wait_seconds,
                )
                self._sleep(wait_seconds)
                attempt += 1
                continue

            if response.status_code >= 400:
                snippet = (response.text or "").strip()[:500]
                raise ApiRequestError(
                    f"HTTP {response.status_code} for {method} {url}: {snippet}"
                )

            try:
                return response.json()
            except ValueError as exc:
                raise ApiRequestError(
                    f"Invalid JSON response for {method} {url}"
                ) from exc

    def _throttle(self) -> None:
        """Rate limiting guard using a rolling 60-second window."""
        now = self._time()
        while self._request_times and now - self._request_times[0] >= 60:
            self._request_times.popleft()

        if len(self._request_times) >= self.rate_limit_per_minute:
            wait_seconds = 60 - (now - self._request_times[0]) + 0.01
            logger.info("Throttling API calls for %.2fs", wait_seconds)
            self._sleep(wait_seconds)
            now = self._time()
            while self._request_times and now - self._request_times[0] >= 60:
                self._request_times.popleft()

        self._request_times.append(now)

    def _resolve_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return f"{self.base_url}/{path_or_url.lstrip('/')}"

    @staticmethod
    def _extract_page(
        payload: Any,
    ) -> tuple[list[Any], str | None, dict[str, Any] | None]:
        items: list[Any] = []
        next_page_uri: str | None = None
        pagination: dict[str, Any] | None = None

        if isinstance(payload, list):
            return payload, None, None

        if not isinstance(payload, dict):
            return [], None, None

        if isinstance(payload.get("data"), list):
            items = payload["data"]
        elif isinstance(payload.get("resources"), list):
            items = payload["resources"]
        elif isinstance(payload.get("data"), dict):
            data_obj = payload["data"]
            if isinstance(data_obj.get("result"), list):
                items = data_obj["result"]
        elif isinstance(payload.get("result"), list):
            items = payload["result"]

        if isinstance(payload.get("next_page_uri"), str):
            next_page_uri = payload["next_page_uri"]
        elif isinstance(payload.get("data"), dict) and isinstance(
            payload["data"].get("next_page_uri"), str
        ):
            next_page_uri = payload["data"]["next_page_uri"]

        meta = payload.get("meta")
        if isinstance(meta, dict) and isinstance(meta.get("pagination"), dict):
            pagination = meta["pagination"]

        return items, next_page_uri, pagination

    @staticmethod
    def _parse_retry_after(header_value: str | None) -> float | None:
        if not header_value:
            return None
        try:
            return max(0.0, float(header_value))
        except (TypeError, ValueError):
            return None

    def _next_from_meta(
        self,
        *,
        original_path: str,
        current_params: dict[str, Any],
        pagination: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any]] | None:
        if not pagination:
            return None

        next_value = pagination.get("next")
        if isinstance(next_value, str):
            stripped = next_value.strip()
            if not stripped:
                return None
            if stripped.startswith("http://") or stripped.startswith("https://"):
                return stripped, {}
            if stripped.isdigit():
                params = dict(current_params)
                params["offset"] = int(stripped)
                return original_path, params
            parsed = urlparse(stripped)
            if parsed.query:
                params = dict(current_params)
                query_map = parse_qs(parsed.query)
                for key, values in query_map.items():
                    if values:
                        params[key] = values[-1]
                return (
                    stripped if stripped.startswith("/") else original_path,
                    params,
                )

        if isinstance(next_value, (int, float)):
            params = dict(current_params)
            params["offset"] = int(next_value)
            return original_path, params

        if isinstance(next_value, dict):
            params = dict(current_params)
            for key in ("offset", "page", "cursor"):
                if key in next_value:
                    params[key] = next_value[key]
            return original_path, params

        if next_value in (None, "", False):
            offset = pagination.get("offset")
            limit = pagination.get("limit")
            total = pagination.get("total")
            if all(isinstance(v, int) for v in (offset, limit, total)):
                if offset + limit < total:
                    params = dict(current_params)
                    params["offset"] = offset + limit
                    params.setdefault("limit", limit)
                    return original_path, params

        return None
