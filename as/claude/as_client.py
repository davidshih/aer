"""Adaptive Shield API client module."""

import logging
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)


class AdaptiveShieldClient:
    """Client for the Adaptive Shield REST API."""

    MAX_RETRIES = 3
    RATE_LIMIT_PER_MIN = 95  # 100 limit with 5-request buffer
    PAGE_SIZE = 100

    def __init__(self, api_key, base_url="https://api.adaptive-shield.com"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        self._request_timestamps = []

    def _throttle(self):
        """Enforce rate limit of ~95 req/min."""
        now = time.monotonic()
        # Drop timestamps older than 60s
        self._request_timestamps = [
            t for t in self._request_timestamps if now - t < 60
        ]
        if len(self._request_timestamps) >= self.RATE_LIMIT_PER_MIN:
            sleep_time = 60 - (now - self._request_timestamps[0])
            if sleep_time > 0:
                logger.info("Rate limit throttle: sleeping %.1fs", sleep_time)
                time.sleep(sleep_time)
        self._request_timestamps.append(time.monotonic())

    def _request(self, method, path, params=None, paginate=True):
        """Universal request handler with pagination, rate limiting, and retries.

        Returns a list of records (paginated) or the raw response dict.
        """
        url = f"{self.base_url}{path}"
        params = dict(params or {})

        if not paginate:
            return self._single_request(method, url, params)

        # Paginated fetch: collect all pages
        all_records = []
        params.setdefault("limit", self.PAGE_SIZE)
        params["offset"] = 0

        while True:
            data = self._single_request(method, url, params)

            # Handle both list responses and wrapped responses
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                # Try common wrapper keys
                records = (
                    data.get("data")
                    or data.get("results")
                    or data.get("items")
                    or []
                )
                if not isinstance(records, list):
                    # Not a paginated response, return as-is
                    return data
            else:
                return data

            all_records.extend(records)

            if len(records) < self.PAGE_SIZE:
                break
            params["offset"] += self.PAGE_SIZE

        return all_records

    def _single_request(self, method, url, params):
        """Execute a single request with throttling and retry logic."""
        for attempt in range(self.MAX_RETRIES):
            self._throttle()
            try:
                resp = self.session.request(method, url, params=params)

                if resp.status_code == 401:
                    raise AuthError(f"Unauthorized (401): check your API key")

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    logger.warning("Rate limited (429), sleeping %ds", retry_after)
                    time.sleep(retry_after)
                    continue

                if resp.status_code >= 500:
                    if attempt < self.MAX_RETRIES - 1:
                        wait = 2 ** attempt
                        logger.warning(
                            "Server error %d, retry %d/%d in %ds",
                            resp.status_code, attempt + 1, self.MAX_RETRIES, wait,
                        )
                        time.sleep(wait)
                        continue
                    resp.raise_for_status()

                resp.raise_for_status()
                return resp.json()

            except requests.ConnectionError as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning("Connection error, retry in %ds: %s", wait, e)
                    time.sleep(wait)
                    continue
                raise

        return []  # Should not reach here, but safe fallback

    # ── Public API methods ──

    def get_accounts(self):
        """List all accounts."""
        return self._request("GET", "/api/v1/accounts")

    def get_alerts(self, account_id, days_back=3):
        """Get configuration drift alerts within the specified timeframe.

        Filters locally for:
        - alert_type = "Security Check Degraded"
        - not archived
        - within days_back window
        """
        alerts = self._request("GET", f"/api/v1/accounts/{account_id}/alerts")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        filtered = []
        for a in alerts:
            # Skip archived
            if a.get("archived") or a.get("is_archived"):
                continue

            # Filter by type
            alert_type = a.get("alert_type") or a.get("type") or ""
            if "security check degraded" not in alert_type.lower():
                continue

            # Filter by time
            ts_str = a.get("timestamp") or a.get("created_at") or a.get("date") or ""
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass  # Keep alert if we can't parse timestamp

            filtered.append(a)

        return filtered

    def get_integrations(self, account_id):
        """Get integrations with failures (status != succeeded or has issues)."""
        integrations = self._request(
            "GET", f"/api/v1/accounts/{account_id}/integrations"
        )

        failed = []
        for i in integrations:
            status = (i.get("status") or "").lower()
            has_issues = bool(i.get("issues") or i.get("errors"))
            if status != "succeeded" or has_issues:
                failed.append(i)

        return failed

    def get_security_check(self, account_id, check_id):
        """Get a single security check's details. Results are cached."""
        cache_key = f"{account_id}:{check_id}"
        if cache_key in self._check_cache:
            return self._check_cache[cache_key]

        try:
            data = self._request(
                "GET",
                f"/api/v1/accounts/{account_id}/security_checks/{check_id}",
                paginate=False,
            )
            self._check_cache[cache_key] = data
            return data
        except Exception as e:
            logger.error("Failed to fetch security check %s: %s", check_id, e)
            return {}

    @property
    def _check_cache(self):
        if not hasattr(self, "__check_cache"):
            self.__check_cache = {}
        return self.__check_cache

    def get_affected_entities(self, account_id, check_id):
        """Get affected entities for a security check."""
        try:
            return self._request(
                "GET",
                f"/api/v1/accounts/{account_id}/security_checks/{check_id}/affected",
            )
        except Exception as e:
            logger.error(
                "Failed to fetch affected entities for check %s: %s", check_id, e
            )
            return []


class AuthError(Exception):
    """Raised when API authentication fails."""
