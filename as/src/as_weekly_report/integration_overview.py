"""Helpers for Adaptive Shield integration overview reporting."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

import pandas as pd

DEFAULT_OUTPUT_TIMEZONE = "America/New_York"
DEFAULT_SNAPSHOT_GRANULARITY = "daily"

RUN_CONTEXT_COLUMNS = [
    "run_ts_utc",
    "run_ts_ny",
    "snapshot_date_utc",
    "snapshot_date_ny",
    "snapshot_hour_utc",
    "snapshot_hour_ny",
    "snapshot_granularity",
]

INTEGRATION_COLUMNS = [
    "account_id",
    "account_name",
    "integration_id",
    "integration_name",
    "integration_alias",
    "saas_name",
    "integration_status",
    "run_ts_utc",
    "run_ts_ny",
    "snapshot_date_utc",
    "snapshot_date_ny",
    "snapshot_hour_utc",
    "snapshot_hour_ny",
    "snapshot_granularity",
]

CHECK_COLUMNS = [
    "account_id",
    "account_name",
    "integration_id",
    "integration_name",
    "integration_alias",
    "saas_name",
    "security_check_id",
    "security_check_name",
    "security_check_details",
    "remediation_steps",
    "impact_level",
    "current_status",
    "is_global",
    "affected_entities_count",
    "affected_scope",
    "affected_entities_detail",
    "last_change_datetime",
    "source",
    "source_id",
    "run_ts_utc",
    "run_ts_ny",
    "snapshot_date_utc",
    "snapshot_date_ny",
    "snapshot_hour_utc",
    "snapshot_hour_ny",
    "snapshot_granularity",
]

FAILED_ENTITY_COLUMNS = [
    "account_id",
    "account_name",
    "integration_id",
    "integration_name",
    "integration_alias",
    "saas_name",
    "security_check_id",
    "security_check_name",
    "current_status",
    "entity_type",
    "entity_name",
    "entity_dismissed",
    "entity_dismissed_reason",
    "entity_dismiss_expiration_date",
    "entity_extra_context_json",
    "entity_usage_json",
    "entity_raw_json",
    "run_ts_utc",
    "run_ts_ny",
    "snapshot_date_utc",
    "snapshot_date_ny",
    "snapshot_hour_utc",
    "snapshot_hour_ny",
    "snapshot_granularity",
]


def _ensure_utc(value: datetime | None) -> datetime:
    dt = value or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_run_context(
    *,
    now_utc: datetime | None = None,
    output_timezone: str = DEFAULT_OUTPUT_TIMEZONE,
    snapshot_granularity: str = DEFAULT_SNAPSHOT_GRANULARITY,
) -> dict[str, str]:
    """Build run context columns with UTC and New York timestamps."""
    utc_dt = _ensure_utc(now_utc)
    ny_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
    output_dt = utc_dt.astimezone(ZoneInfo(output_timezone))

    return {
        "run_ts_utc": utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_ts_ny": ny_dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "snapshot_date_utc": utc_dt.strftime("%Y-%m-%d"),
        "snapshot_date_ny": ny_dt.strftime("%Y-%m-%d"),
        "snapshot_hour_utc": utc_dt.strftime("%H"),
        "snapshot_hour_ny": ny_dt.strftime("%H"),
        "snapshot_granularity": snapshot_granularity,
        "snapshot_date_output": output_dt.strftime("%Y-%m-%d"),
        "output_timezone": output_timezone,
    }


def add_run_context_columns(
    frame: pd.DataFrame,
    run_context: dict[str, Any],
) -> pd.DataFrame:
    """Attach run context fields to a dataframe copy."""
    result = frame.copy()
    for column in RUN_CONTEXT_COLUMNS:
        result[column] = run_context[column]
    return result


def build_output_dirs(
    output_root: str | Path,
    run_context: dict[str, Any],
) -> dict[str, Path]:
    """Build output directories under output/YYYY-MM-DD/Adaptive_Shield."""
    base = (
        Path(output_root)
        / str(run_context["snapshot_date_ny"])
        / "Adaptive_Shield"
    )
    dirs = {
        "root": base,
        "log": base / "log",
        "overview": base / "overview",
        "history": base / "history",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def normalize_status(raw: Any) -> str:
    """Normalize status text to stable labels."""
    if raw is None:
        return "unknown"

    value = str(raw).strip().lower()
    if not value:
        return "unknown"
    if "fail" in value:
        return "failed"
    if "pass" in value:
        return "passed"
    if "degrad" in value:
        return "degraded"
    if "drift" in value:
        return "drifted"
    if "dismiss" in value:
        return "dismissed"
    if "pend" in value:
        return "pending"
    return value


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _integration_id_from_record(record: dict[str, Any]) -> str:
    integration_obj = (
        record.get("integration")
        if isinstance(record.get("integration"), dict)
        else {}
    )
    candidates = [
        record.get("id"),
        record.get("integration_id"),
        record.get("integrationId"),
        integration_obj.get("id"),
    ]
    for candidate in candidates:
        if candidate not in (None, ""):
            return str(candidate)
    return ""


def normalize_integration_records(
    *,
    account_id: str,
    account_name: str,
    integration_records: Iterable[dict[str, Any]],
    run_context: dict[str, Any],
) -> pd.DataFrame:
    """Normalize integration records with stable output columns."""
    rows: list[dict[str, Any]] = []
    for record in integration_records:
        if not isinstance(record, dict):
            continue

        integration_id = _integration_id_from_record(record)
        if not integration_id:
            continue

        rows.append(
            {
                "account_id": account_id,
                "account_name": account_name,
                "integration_id": integration_id,
                "integration_name": record.get("name") or record.get("integration_name"),
                "integration_alias": record.get("alias") or record.get("integration_alias"),
                "saas_name": record.get("saas_name") or record.get("saas") or record.get("name"),
                "integration_status": normalize_status(record.get("status") or record.get("state")),
                **{column: run_context[column] for column in RUN_CONTEXT_COLUMNS},
            }
        )

    df = pd.DataFrame(rows, columns=INTEGRATION_COLUMNS)
    if df.empty:
        return df

    return (
        df.sort_values(["account_id", "integration_id", "run_ts_utc"]) 
        .drop_duplicates(subset=["account_id", "integration_id"], keep="last")
        .reset_index(drop=True)
    )


def resolve_check_integration_id(check: dict[str, Any]) -> str:
    """Resolve integration ID from a check payload."""
    integration_obj = (
        check.get("integration")
        if isinstance(check.get("integration"), dict)
        else {}
    )
    candidates = [
        check.get("integration_id"),
        check.get("Integration_id"),
        check.get("integrationId"),
        integration_obj.get("id"),
    ]

    for candidate in candidates:
        if candidate not in (None, ""):
            return str(candidate)

    return ""


def _integration_lookup(integrations_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if integrations_df.empty:
        return {}

    lookup: dict[str, dict[str, Any]] = {}
    for row in integrations_df.to_dict("records"):
        integration_id = str(row.get("integration_id") or "")
        if integration_id:
            lookup[integration_id] = row
    return lookup


def normalize_check_records(
    *,
    account_id: str,
    account_name: str,
    check_records: Iterable[dict[str, Any]],
    integrations_df: pd.DataFrame,
    run_context: dict[str, Any],
    strict_mapping: bool = True,
) -> pd.DataFrame:
    """Normalize full security check inventory for one account."""
    integration_map = _integration_lookup(integrations_df)
    rows: list[dict[str, Any]] = []

    for record in check_records:
        if not isinstance(record, dict):
            continue

        security_check_id = str(
            record.get("id")
            or record.get("security_check_id")
            or record.get("source_id")
            or ""
        )
        if not security_check_id:
            continue

        integration_id = resolve_check_integration_id(record)
        if not integration_id and strict_mapping:
            raise ValueError(
                f"Check {security_check_id} cannot be mapped to an integration."
            )

        integration_info = integration_map.get(integration_id, {})
        if strict_mapping and integration_id and not integration_info:
            raise ValueError(
                f"Check {security_check_id} references unknown integration {integration_id}."
            )

        current_status = normalize_status(
            record.get("status") or record.get("current_status")
        )
        is_global = bool(record.get("is_global"))

        affected_count = record.get("affected")
        if affected_count in (None, ""):
            affected_count = record.get("affected_entities_count")

        if is_global:
            affected_scope = "global"
            affected_entities_count: Any = "global"
            affected_entities_detail = "global"
        else:
            affected_scope = str(record.get("affected_scope") or "entity").lower()
            if affected_scope not in {"entity", "entity_diff", "unresolved"}:
                affected_scope = "entity"
            affected_entities_count = affected_count
            affected_entities_detail = record.get("affected_entities_detail") or ""

        rows.append(
            {
                "account_id": account_id,
                "account_name": account_name,
                "integration_id": integration_id,
                "integration_name": integration_info.get("integration_name"),
                "integration_alias": integration_info.get("integration_alias"),
                "saas_name": integration_info.get("saas_name"),
                "security_check_id": security_check_id,
                "security_check_name": record.get("name") or record.get("title"),
                "security_check_details": record.get("details") or record.get("description"),
                "remediation_steps": record.get("remediation_plan") or record.get("remediation"),
                "impact_level": record.get("impact") or record.get("severity"),
                "current_status": current_status,
                "is_global": is_global,
                "affected_entities_count": affected_entities_count,
                "affected_scope": affected_scope,
                "affected_entities_detail": affected_entities_detail,
                "last_change_datetime": (
                    record.get("updated_at")
                    or record.get("timestamp")
                    or record.get("change_datetime")
                ),
                "source": record.get("source") or "security_checks",
                "source_id": record.get("source_id") or security_check_id,
                **{column: run_context[column] for column in RUN_CONTEXT_COLUMNS},
            }
        )

    df = pd.DataFrame(rows, columns=CHECK_COLUMNS)
    if df.empty:
        return df

    return (
        df.sort_values(["account_id", "integration_id", "security_check_id", "run_ts_utc"]) 
        .drop_duplicates(
            subset=["account_id", "integration_id", "security_check_id"],
            keep="last",
        )
        .reset_index(drop=True)
    )


def endpoint_is_unavailable(exc: Exception) -> bool:
    """Detect endpoint-not-available failures for fallback logic."""
    message = str(exc).lower()
    tokens = (
        "http 404",
        "http 405",
        "http 501",
        "not found",
        "method not allowed",
        "unsupported",
    )
    return any(token in message for token in tokens)


def select_checks_inventory_strict(
    *,
    account_id: str,
    integration_ids: Iterable[str],
    fetch_account_checks: Callable[[], list[dict[str, Any]]],
    fetch_integration_checks: Callable[[str], list[dict[str, Any]]],
    unavailable_predicate: Callable[[Exception], bool] = endpoint_is_unavailable,
) -> tuple[list[dict[str, Any]], str]:
    """Select strict full-check inventory with endpoint fallback rules."""
    account_checks: list[dict[str, Any]] = []
    account_error: Exception | None = None

    try:
        account_checks = fetch_account_checks()
    except Exception as exc:  # pragma: no cover - behavior validated via tests
        account_error = exc

    clean_integration_ids = [
        str(integration_id)
        for integration_id in integration_ids
        if str(integration_id or "").strip()
    ]

    integration_checks: list[dict[str, Any]] = []
    integration_errors: list[tuple[str, Exception]] = []
    unavailable_count = 0

    for integration_id in clean_integration_ids:
        try:
            rows = fetch_integration_checks(integration_id)
            for row in rows:
                if not isinstance(row, dict):
                    continue
                enriched = dict(row)
                if not resolve_check_integration_id(enriched):
                    enriched["integration_id"] = integration_id
                integration_checks.append(enriched)
        except Exception as exc:
            if unavailable_predicate(exc):
                unavailable_count += 1
                continue
            integration_errors.append((integration_id, exc))

    if integration_errors:
        details = ", ".join(
            f"{integration_id}: {error}"
            for integration_id, error in integration_errors
        )
        raise RuntimeError(
            "Integration-level checks endpoint failed for one or more integrations "
            f"in account {account_id}: {details}"
        )

    if clean_integration_ids and integration_checks:
        if unavailable_count:
            raise RuntimeError(
                "Integration-level checks endpoint is only available for a subset "
                f"of integrations in account {account_id}."
            )
        return integration_checks, "integration_level"

    integration_endpoint_unavailable = (
        bool(clean_integration_ids)
        and unavailable_count == len(clean_integration_ids)
    )

    if account_error is None:
        return account_checks, "account_level"

    if integration_endpoint_unavailable:
        raise RuntimeError(
            "No supported security checks endpoint found for account "
            f"{account_id}."
        ) from account_error

    raise RuntimeError(
        f"Cannot build strict checks inventory for account {account_id}."
    ) from account_error


def build_failed_entities_df(
    failed_entity_records: Iterable[dict[str, Any]],
    run_context: dict[str, Any],
) -> pd.DataFrame:
    """Normalize failed check affected entities into a flat table."""
    rows: list[dict[str, Any]] = []

    for item in failed_entity_records:
        if not isinstance(item, dict):
            continue

        entity = item.get("entity") if isinstance(item.get("entity"), dict) else item
        if not isinstance(entity, dict):
            continue

        rows.append(
            {
                "account_id": item.get("account_id"),
                "account_name": item.get("account_name"),
                "integration_id": item.get("integration_id"),
                "integration_name": item.get("integration_name"),
                "integration_alias": item.get("integration_alias"),
                "saas_name": item.get("saas_name"),
                "security_check_id": item.get("security_check_id"),
                "security_check_name": item.get("security_check_name"),
                "current_status": normalize_status(item.get("current_status")),
                "entity_type": entity.get("type"),
                "entity_name": entity.get("entity_name") or entity.get("name"),
                "entity_dismissed": entity.get("dismissed"),
                "entity_dismissed_reason": entity.get("dismissed_reason"),
                "entity_dismiss_expiration_date": entity.get("dismiss_expiration_date"),
                "entity_extra_context_json": _to_json(entity.get("extra_context")),
                "entity_usage_json": _to_json(entity.get("usage")),
                "entity_raw_json": _to_json(entity),
                **{column: run_context[column] for column in RUN_CONTEXT_COLUMNS},
            }
        )

    return pd.DataFrame(rows, columns=FAILED_ENTITY_COLUMNS)


def parquet_supported() -> bool:
    """Return True if a parquet engine is installed."""
    try:
        import pyarrow  # noqa: F401

        return True
    except ModuleNotFoundError:
        try:
            import fastparquet  # noqa: F401

            return True
        except ModuleNotFoundError:
            return False


def ensure_parquet_support() -> None:
    """Raise with an actionable message if parquet engine is missing."""
    if not parquet_supported():
        raise RuntimeError(
            "Parquet support is required. Install pyarrow (recommended) "
            "or fastparquet before running history snapshots."
        )


def build_history_partition_dir(
    history_root: str | Path,
    *,
    dataset: str,
    run_context: dict[str, Any],
    granularity: str | None = None,
) -> Path:
    """Build history partition directory using UTC partition keys."""
    partition_granularity = granularity or str(run_context["snapshot_granularity"])
    base = (
        Path(history_root)
        / dataset
        / f"granularity={partition_granularity}"
        / f"snapshot_date_utc={run_context['snapshot_date_utc']}"
    )
    if partition_granularity == "hourly":
        base = base / f"snapshot_hour_utc={run_context['snapshot_hour_utc']}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _run_ts_token(run_context: dict[str, Any]) -> str:
    return str(run_context["run_ts_utc"]).replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")


def write_snapshot_parquet(
    frame: pd.DataFrame,
    history_root: str | Path,
    *,
    dataset: str,
    run_context: dict[str, Any],
    file_prefix: str,
) -> Path:
    """Write a snapshot frame to partitioned parquet path."""
    ensure_parquet_support()

    output_frame = frame.copy()
    for column in RUN_CONTEXT_COLUMNS:
        if column not in output_frame.columns:
            output_frame[column] = run_context[column]

    partition_dir = build_history_partition_dir(
        history_root,
        dataset=dataset,
        run_context=run_context,
    )
    output_path = partition_dir / f"{file_prefix}_{_run_ts_token(run_context)}.parquet"
    output_frame.to_parquet(output_path, index=False)
    return output_path


def read_snapshot_history(
    history_root: str | Path,
    *,
    dataset: str,
    lookback_days: int | None = None,
    now_utc: datetime | None = None,
) -> pd.DataFrame:
    """Read snapshot parquet files and optionally apply UTC date lookback."""
    ensure_parquet_support()

    dataset_root = Path(history_root) / dataset
    if not dataset_root.exists():
        return pd.DataFrame()

    files = sorted(dataset_root.rglob("*.parquet"))
    if not files:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = [pd.read_parquet(file_path) for file_path in files]
    combined = pd.concat(frames, ignore_index=True, sort=False)

    if lookback_days is None or "snapshot_date_utc" not in combined.columns:
        return combined

    cutoff = _ensure_utc(now_utc).date().toordinal() - int(lookback_days)

    date_series = pd.to_datetime(
        combined["snapshot_date_utc"],
        errors="coerce",
        utc=True,
    ).dt.date
    keep_mask = date_series.apply(
        lambda item: item.toordinal() >= cutoff if item is not None else False
    )
    return combined[keep_mask].reset_index(drop=True)


def dedupe_daily_history(
    history_df: pd.DataFrame,
    *,
    key_columns: Iterable[str],
) -> pd.DataFrame:
    """Keep the latest run per key and per NY snapshot date."""
    if history_df.empty:
        return history_df.copy()

    required = [*key_columns, "snapshot_date_ny", "run_ts_utc"]
    missing = [column for column in required if column not in history_df.columns]
    if missing:
        raise ValueError(f"Missing history columns for dedupe: {', '.join(missing)}")

    ordered = history_df.sort_values("run_ts_utc")
    dedupe_subset = [*key_columns, "snapshot_date_ny"]
    deduped = ordered.drop_duplicates(subset=dedupe_subset, keep="last")
    return deduped.sort_values(["snapshot_date_ny", "run_ts_utc"], ascending=[False, False]).reset_index(drop=True)


def build_check_history_map(
    history_df: pd.DataFrame,
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    """Group history rows by check key for notebook UI rendering."""
    if history_df.empty:
        return {}

    required = ["account_id", "integration_id", "security_check_id", "snapshot_date_ny", "run_ts_utc"]
    missing = [column for column in required if column not in history_df.columns]
    if missing:
        raise ValueError(f"Missing columns for history map: {', '.join(missing)}")

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for (account_id, integration_id, security_check_id), group in history_df.groupby(
        ["account_id", "integration_id", "security_check_id"],
        dropna=False,
    ):
        rows = group.sort_values(
            ["snapshot_date_ny", "run_ts_utc"],
            ascending=[False, False],
        ).to_dict("records")
        grouped[(str(account_id), str(integration_id), str(security_check_id))] = rows
    return grouped


def build_overview_export_paths(overview_dir: str | Path, ts: str) -> dict[str, Path]:
    """Build canonical export file paths for integration overview outputs."""
    root = Path(overview_dir)
    return {
        "xlsx_path": root / f"AS_Integrations_Overview_{ts}.xlsx",
        "summary_csv_path": root / f"AS_Integrations_Summary_{ts}.csv",
        "checks_csv_path": root / f"AS_Integrations_Checks_{ts}.csv",
        "entities_csv_path": root / f"AS_Integrations_Entities_{ts}.csv",
        "errors_csv_path": root / f"AS_Integrations_Errors_{ts}.csv",
    }


def export_integration_overview(
    *,
    summary_df: pd.DataFrame,
    checks_df: pd.DataFrame,
    entities_df: pd.DataFrame,
    errors_df: pd.DataFrame,
    overview_dir: str | Path,
    ts: str,
    export_xlsx: bool = True,
    export_csv: bool = True,
) -> dict[str, str]:
    """Export integration overview outputs in XLSX and CSV formats."""
    overview_path = Path(overview_dir)
    overview_path.mkdir(parents=True, exist_ok=True)

    file_paths = build_overview_export_paths(overview_path, ts)
    results = {key: "" for key in file_paths}

    if export_xlsx:
        with pd.ExcelWriter(file_paths["xlsx_path"], engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="integrations", index=False)
            checks_df.to_excel(writer, sheet_name="checks", index=False)
            entities_df.to_excel(writer, sheet_name="entities", index=False)
            errors_df.to_excel(writer, sheet_name="errors", index=False)
        results["xlsx_path"] = str(file_paths["xlsx_path"])

    if export_csv:
        summary_df.to_csv(file_paths["summary_csv_path"], index=False)
        checks_df.to_csv(file_paths["checks_csv_path"], index=False)
        entities_df.to_csv(file_paths["entities_csv_path"], index=False)
        errors_df.to_csv(file_paths["errors_csv_path"], index=False)

        results["summary_csv_path"] = str(file_paths["summary_csv_path"])
        results["checks_csv_path"] = str(file_paths["checks_csv_path"])
        results["entities_csv_path"] = str(file_paths["entities_csv_path"])
        results["errors_csv_path"] = str(file_paths["errors_csv_path"])

    return results


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    """Write a JSON file with deterministic formatting."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def write_history_manifest(
    history_dir: str | Path,
    *,
    run_context: dict[str, Any],
    payload: dict[str, Any],
) -> Path:
    """Write history manifest under history directory."""
    output = Path(history_dir) / f"history_manifest_{_run_ts_token(run_context)}.json"
    return write_json(output, payload)


def write_run_log(
    log_dir: str | Path,
    *,
    run_context: dict[str, Any],
    payload: dict[str, Any],
) -> Path:
    """Write run log file under log directory."""
    output = Path(log_dir) / f"run_log_{_run_ts_token(run_context)}.json"
    return write_json(output, payload)


__all__ = [
    "CHECK_COLUMNS",
    "DEFAULT_OUTPUT_TIMEZONE",
    "DEFAULT_SNAPSHOT_GRANULARITY",
    "FAILED_ENTITY_COLUMNS",
    "INTEGRATION_COLUMNS",
    "RUN_CONTEXT_COLUMNS",
    "add_run_context_columns",
    "build_check_history_map",
    "build_failed_entities_df",
    "build_history_partition_dir",
    "build_output_dirs",
    "build_overview_export_paths",
    "build_run_context",
    "dedupe_daily_history",
    "endpoint_is_unavailable",
    "ensure_parquet_support",
    "export_integration_overview",
    "normalize_check_records",
    "normalize_integration_records",
    "normalize_status",
    "parquet_supported",
    "read_snapshot_history",
    "resolve_check_integration_id",
    "select_checks_inventory_strict",
    "write_history_manifest",
    "write_run_log",
    "write_snapshot_parquet",
]
