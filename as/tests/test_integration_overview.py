"""Unit tests for integration overview helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from as_weekly_report.integration_overview import (
    build_check_history_map,
    build_history_partition_dir,
    build_output_dirs,
    build_run_context,
    dedupe_daily_history,
    normalize_check_records,
    normalize_integration_records,
    read_snapshot_history,
    select_checks_inventory_strict,
    write_snapshot_parquet,
)


def test_build_run_context_contains_utc_and_new_york_fields() -> None:
    context = build_run_context(
        now_utc=datetime(2026, 2, 17, 12, 30, tzinfo=timezone.utc),
    )

    assert context["run_ts_utc"] == "2026-02-17T12:30:00Z"
    assert context["snapshot_date_utc"] == "2026-02-17"
    assert context["snapshot_date_ny"] == "2026-02-17"
    assert context["snapshot_hour_utc"] == "12"
    assert context["snapshot_hour_ny"] == "07"


def test_build_output_dirs_uses_new_york_date(tmp_path: Path) -> None:
    context = build_run_context(
        now_utc=datetime(2026, 2, 17, 1, 15, tzinfo=timezone.utc),
    )
    dirs = build_output_dirs(tmp_path, context)

    assert dirs["root"] == tmp_path / "2026-02-16" / "Adaptive_Shield"
    assert dirs["log"].exists()
    assert dirs["overview"].exists()
    assert dirs["history"].exists()


def test_history_partition_builder_supports_daily_and_hourly(tmp_path: Path) -> None:
    context = build_run_context(
        now_utc=datetime(2026, 2, 17, 12, 30, tzinfo=timezone.utc),
        snapshot_granularity="daily",
    )
    daily = build_history_partition_dir(
        tmp_path,
        dataset="check_snapshot",
        run_context=context,
    )
    hourly = build_history_partition_dir(
        tmp_path,
        dataset="check_snapshot",
        run_context=context,
        granularity="hourly",
    )

    assert "granularity=daily" in str(daily)
    assert "snapshot_date_utc=2026-02-17" in str(daily)
    assert "granularity=hourly" in str(hourly)
    assert "snapshot_hour_utc=12" in str(hourly)


def test_select_checks_inventory_prefers_integration_level() -> None:
    account_calls = {"count": 0}
    integration_calls = {"count": 0}

    def fetch_account_checks() -> list[dict[str, Any]]:
        account_calls["count"] += 1
        return [{"id": "acc-check", "integration_id": "int-1"}]

    def fetch_integration_checks(integration_id: str) -> list[dict[str, Any]]:
        integration_calls["count"] += 1
        return [{"id": f"{integration_id}-check"}]

    rows, source = select_checks_inventory_strict(
        account_id="acc-1",
        integration_ids=["int-1", "int-2"],
        fetch_account_checks=fetch_account_checks,
        fetch_integration_checks=fetch_integration_checks,
    )

    assert source == "integration_level"
    assert integration_calls["count"] == 2
    assert account_calls["count"] == 1
    assert {row["integration_id"] for row in rows} == {"int-1", "int-2"}


def test_select_checks_inventory_falls_back_to_account_level() -> None:
    def fetch_account_checks() -> list[dict[str, Any]]:
        return [{"id": "check-1", "integration_id": "int-1"}]

    def fetch_integration_checks(_integration_id: str) -> list[dict[str, Any]]:
        raise RuntimeError("HTTP 404 for GET /security_checks")

    rows, source = select_checks_inventory_strict(
        account_id="acc-1",
        integration_ids=["int-1", "int-2"],
        fetch_account_checks=fetch_account_checks,
        fetch_integration_checks=fetch_integration_checks,
    )

    assert source == "account_level"
    assert rows == [{"id": "check-1", "integration_id": "int-1"}]


def test_select_checks_inventory_raises_when_all_endpoints_fail() -> None:
    def fetch_account_checks() -> list[dict[str, Any]]:
        raise RuntimeError("HTTP 404 for GET /api/v1/accounts/acc-1/security_checks")

    def fetch_integration_checks(_integration_id: str) -> list[dict[str, Any]]:
        raise RuntimeError("HTTP 404 for GET /api/v1/accounts/acc-1/integrations/int-1/security_checks")

    with pytest.raises(RuntimeError):
        select_checks_inventory_strict(
            account_id="acc-1",
            integration_ids=["int-1"],
            fetch_account_checks=fetch_account_checks,
            fetch_integration_checks=fetch_integration_checks,
        )


def test_normalize_check_records_requires_mappable_integration() -> None:
    run_context = build_run_context(
        now_utc=datetime(2026, 2, 17, 12, 30, tzinfo=timezone.utc),
    )
    integrations_df = normalize_integration_records(
        account_id="acc-1",
        account_name="Prod",
        integration_records=[{"id": "int-1", "name": "Slack", "status": "succeeded"}],
        run_context=run_context,
    )

    with pytest.raises(ValueError):
        normalize_check_records(
            account_id="acc-1",
            account_name="Prod",
            check_records=[{"id": "check-1", "name": "Require MFA"}],
            integrations_df=integrations_df,
            run_context=run_context,
            strict_mapping=True,
        )


def test_snapshot_write_read_and_daily_dedupe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    storage: dict[str, pd.DataFrame] = {}

    def fake_to_parquet(self: pd.DataFrame, path: Any, index: bool = False) -> None:
        _ = index
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("stub", encoding="utf-8")
        storage[str(output_path)] = self.copy()

    def fake_read_parquet(path: Any) -> pd.DataFrame:
        return storage[str(Path(path))].copy()

    monkeypatch.setattr(
        "as_weekly_report.integration_overview.parquet_supported",
        lambda: True,
    )
    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)
    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    history_root = tmp_path / "history"

    context_1 = build_run_context(
        now_utc=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
    )
    context_2 = build_run_context(
        now_utc=datetime(2026, 2, 17, 18, 0, tzinfo=timezone.utc),
    )

    check_rows_1 = pd.DataFrame(
        [
            {
                "account_id": "acc-1",
                "integration_id": "int-1",
                "security_check_id": "check-1",
                "current_status": "failed",
            }
        ]
    )
    check_rows_2 = pd.DataFrame(
        [
            {
                "account_id": "acc-1",
                "integration_id": "int-1",
                "security_check_id": "check-1",
                "current_status": "passed",
            }
        ]
    )

    write_snapshot_parquet(
        check_rows_1,
        history_root,
        dataset="check_snapshot",
        run_context=context_1,
        file_prefix="check_snapshot",
    )
    write_snapshot_parquet(
        check_rows_2,
        history_root,
        dataset="check_snapshot",
        run_context=context_2,
        file_prefix="check_snapshot",
    )

    history_df = read_snapshot_history(
        history_root,
        dataset="check_snapshot",
    )
    deduped = dedupe_daily_history(
        history_df,
        key_columns=["account_id", "integration_id", "security_check_id"],
    )
    grouped = build_check_history_map(deduped)

    key = ("acc-1", "int-1", "check-1")
    assert len(history_df) == 2
    assert len(deduped) == 1
    assert grouped[key][0]["current_status"] == "passed"
