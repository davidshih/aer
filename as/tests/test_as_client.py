"""Unit tests for AdaptiveShieldClient."""

from __future__ import annotations

from typing import Any

import pytest

from as_weekly_report.as_client import AdaptiveShieldClient, AuthenticationError


class FakeResponse:
    """Minimal response object for client tests."""

    def __init__(
        self,
        *,
        status_code: int,
        payload: Any = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload


class FakeSession:
    """Minimal session object for request stubbing."""

    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.headers: dict[str, str] = {}

    def request(self, *args: Any, **kwargs: Any) -> FakeResponse:
        _ = args
        _ = kwargs
        return self._response


def test_client_sets_token_header() -> None:
    client = AdaptiveShieldClient(api_key="abc123")
    assert client._session.headers["Authorization"] == "Token abc123"


def test_paginate_uses_next_page_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AdaptiveShieldClient(api_key="token")
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def fake_request(
        method: str,
        path_or_url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        _ = method
        calls.append((path_or_url, params))
        if path_or_url == "/api/v1/example":
            return {
                "data": [{"id": "1", "value": "first"}],
                "next_page_uri": "https://api.adaptive-shield.com/page2",
            }
        return {"data": [{"id": "2", "value": "second"}]}

    monkeypatch.setattr(client, "_request", fake_request)
    records = client._paginate("GET", "/api/v1/example")

    assert [item["id"] for item in records] == ["1", "2"]
    assert calls[0][0] == "/api/v1/example"
    assert calls[1][0] == "https://api.adaptive-shield.com/page2"


def test_paginate_uses_meta_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AdaptiveShieldClient(api_key="token")
    offsets_seen: list[int] = []

    def fake_request(
        method: str,
        path_or_url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        _ = method
        assert path_or_url == "/api/v1/affected"
        current_offset = int((params or {}).get("offset", 0))
        offsets_seen.append(current_offset)

        if current_offset == 0:
            return {
                "resources": [{"id": "A"}],
                "meta": {
                    "pagination": {
                        "limit": 1,
                        "offset": 0,
                        "total": 2,
                        "next": 1,
                        "previous": None,
                    }
                },
            }
        return {
            "resources": [{"id": "B"}],
            "meta": {
                "pagination": {
                    "limit": 1,
                    "offset": 1,
                    "total": 2,
                    "next": None,
                    "previous": 0,
                }
            },
        }

    monkeypatch.setattr(client, "_request", fake_request)
    records = client._paginate(
        "GET",
        "/api/v1/affected",
        params={"limit": 1, "offset": 0},
    )

    assert [item["id"] for item in records] == ["A", "B"]
    assert offsets_seen == [0, 1]


def test_get_alerts_passes_type_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = AdaptiveShieldClient(api_key="token")
    captured = {}

    def fake_paginate(
        method: str,
        path_or_url: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        captured["method"] = method
        captured["path_or_url"] = path_or_url
        captured["params"] = params
        return []

    monkeypatch.setattr(client, "_paginate", fake_paginate)
    client.get_alerts(
        account_id="acc-1",
        from_date="2026-02-14T00:00:00Z",
        to_date="2026-02-17T00:00:00Z",
        alert_type="configuration_drift",
    )

    assert captured["method"] == "GET"
    assert captured["path_or_url"] == "/api/v1/accounts/acc-1/alerts"
    assert captured["params"]["type"] == "configuration_drift"


def test_request_fails_fast_on_401() -> None:
    fake_session = FakeSession(FakeResponse(status_code=401, text="Unauthorized"))
    client = AdaptiveShieldClient(
        api_key="token",
        session=fake_session,  # type: ignore[arg-type]
    )

    with pytest.raises(AuthenticationError):
        client._request("GET", "/api/v1/accounts")
