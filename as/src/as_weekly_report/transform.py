"""Data transformation helpers for Adaptive Shield weekly reports."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

SUMMARY_COLUMNS = [
    "change_datetime",
    "security_check_name",
    "security_check_details",
    "remediation_steps",
    "impact_level",
    "current_status",
    "affected_entities_count",
    "affected_scope",
    "affected_entities_detail",
    "account_id",
    "account_name",
    "integration_id",
    "integration_name",
    "integration_alias",
    "security_check_id",
    "alert_id",
    "alert_type",
    "source",
    "source_id",
    "is_archived",
    "ticket_number",
    "ticket_owner",
    "ticket_status",
    "ticket_last_update_datetime",
    "ticket_last_update_content",
    "extracted_at_utc",
]

ENTITY_COLUMNS = [
    "account_id",
    "security_check_id",
    "alert_id",
    "entity_type",
    "entity_name",
    "entity_dismissed",
    "entity_dismissed_reason",
    "entity_dismiss_expiration_date",
    "entity_extra_context_json",
    "entity_usage_json",
    "entity_raw_json",
]

TARGET_ALERT_TYPES = {"configuration_drift", "integration_failure"}

_TYPE_ALIAS_MAP = {
    "security_check_degraded": "check_degraded",
    "security_check_degrade": "check_degraded",
    "securitycheckdegraded": "check_degraded",
    "threat": "threat",
}


def normalize_alert_type(raw: Any) -> str:
    """Normalize alert type values from API and UI variants."""
    if raw is None:
        return ""

    value = str(raw).strip().lower()
    value = value.replace("-", "_").replace(" ", "_")
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")

    return _TYPE_ALIAS_MAP.get(value, value)


def filter_target_alerts(
    rows: Iterable[dict[str, Any]],
    *,
    include_check_degraded: bool = False,
) -> list[dict[str, Any]]:
    """Filter alerts to reportable types and exclude archived records."""
    targets = set(TARGET_ALERT_TYPES)
    if include_check_degraded:
        targets.add("check_degraded")

    filtered: list[dict[str, Any]] = []
    for row in rows:
        normalized = normalize_alert_type(row.get("alert_type") or row.get("type"))
        is_archived = bool(row.get("is_archived"))
        if is_archived:
            continue
        if normalized not in targets:
            continue

        item = dict(row)
        item["alert_type_normalized"] = normalized
        filtered.append(item)

    return filtered


def extract_security_check_id(alert: dict[str, Any]) -> str:
    """Resolve security check ID from source_id or check API link."""
    for key in ("source_id", "security_check_id"):
        value = alert.get(key)
        if value:
            return str(value)

    api_link = alert.get("security_check_api_link")
    if not api_link:
        return ""

    match = re.search(r"/security_checks/([^/?#]+)", str(api_link))
    if match:
        return match.group(1)
    return ""


def build_entities_df(entity_records: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Build normalized entities table from affected entity API results."""
    rows: list[dict[str, Any]] = []

    for record in entity_records:
        account_id = record.get("account_id")
        alert_id = record.get("alert_id")
        security_check_id = record.get("security_check_id")
        entity = record.get("entity") if isinstance(record.get("entity"), dict) else record
        if not isinstance(entity, dict):
            continue

        rows.append(
            {
                "account_id": account_id,
                "security_check_id": security_check_id,
                "alert_id": alert_id,
                "entity_type": entity.get("type"),
                "entity_name": entity.get("entity_name") or entity.get("name"),
                "entity_dismissed": entity.get("dismissed"),
                "entity_dismissed_reason": entity.get("dismissed_reason"),
                "entity_dismiss_expiration_date": entity.get("dismiss_expiration_date"),
                "entity_extra_context_json": _to_json(entity.get("extra_context")),
                "entity_usage_json": _to_json(entity.get("usage")),
                "entity_raw_json": _to_json(entity),
            }
        )

    return pd.DataFrame(rows, columns=ENTITY_COLUMNS)


def build_summary_df(
    *,
    alerts: Iterable[dict[str, Any]],
    checks: Iterable[dict[str, Any]],
    entities: Iterable[dict[str, Any]],
    accounts: Iterable[dict[str, Any]] | None = None,
    extracted_at_utc: str | None = None,
) -> pd.DataFrame:
    """Build weekly summary table from alerts, checks, and entities."""
    extracted_at = extracted_at_utc or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    account_name_by_id: dict[str, str] = {}
    if accounts:
        for account in accounts:
            account_id = str(account.get("id") or account.get("account_id") or "")
            if account_id:
                account_name_by_id[account_id] = (
                    str(account.get("name") or account.get("account_name") or "")
                )

    checks_by_alert: dict[str, dict[str, Any]] = {}
    checks_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict):
            continue
        alert_id = str(check.get("alert_id") or "")
        account_id = str(check.get("account_id") or "")
        security_check_id = str(
            check.get("security_check_id")
            or check.get("id")
            or check.get("source_id")
            or ""
        )

        if alert_id:
            checks_by_alert[alert_id] = check
        if account_id and security_check_id:
            checks_by_pair[(account_id, security_check_id)] = check

    entity_names_by_alert: dict[str, list[str]] = defaultdict(list)
    entity_count_by_alert: dict[str, int] = defaultdict(int)
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        alert_id = str(entity.get("alert_id") or "")
        if not alert_id:
            continue
        entity_name = entity.get("entity_name")
        if entity_name:
            entity_names_by_alert[alert_id].append(str(entity_name))
        entity_count_by_alert[alert_id] += 1

    rows: list[dict[str, Any]] = []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue

        alert_id = str(alert.get("id") or alert.get("alert_id") or "")
        account_id = str(alert.get("account_id") or "")
        source_id = str(alert.get("source_id") or "")
        security_check_id = extract_security_check_id(alert) or source_id
        check = checks_by_alert.get(alert_id)
        if check is None and account_id and security_check_id:
            check = checks_by_pair.get((account_id, security_check_id), {})
        check = check or {}

        integration_obj = (
            alert.get("integration")
            if isinstance(alert.get("integration"), dict)
            else {}
        )
        if not integration_obj and isinstance(check.get("integration"), dict):
            integration_obj = check["integration"]

        is_global = bool(check.get("is_global"))
        entity_names = sorted(set(entity_names_by_alert.get(alert_id, [])))
        affected_diff = alert.get("affected_diff")
        affected_diff_names: list[str] = []
        if isinstance(affected_diff, list):
            affected_diff_names = [str(item) for item in affected_diff if item is not None]

        affected_scope = "global" if is_global else "unresolved"
        if not is_global:
            if entity_names:
                affected_scope = "entity"
            elif affected_diff_names:
                affected_scope = "entity_diff"

        affected_entities_count: Any
        if is_global:
            affected_entities_count = "global"
        else:
            affected_entities_count = (
                check.get("affected")
                if check.get("affected") not in (None, "")
                else alert.get("new_affected_count")
            )
            if affected_entities_count in (None, "") and entity_count_by_alert.get(alert_id):
                affected_entities_count = entity_count_by_alert[alert_id]

        if is_global:
            affected_entities_detail = "global"
        elif entity_names:
            affected_entities_detail = "; ".join(entity_names)
        elif affected_diff_names:
            affected_entities_detail = "; ".join(affected_diff_names)
        else:
            affected_entities_detail = ""

        current_status = check.get("status")
        if not current_status:
            current_status = _fallback_status_from_alert(alert)

        row = {
            "change_datetime": alert.get("timestamp"),
            "security_check_name": check.get("name") or check.get("title"),
            "security_check_details": check.get("details") or alert.get("description"),
            "remediation_steps": check.get("remediation_plan"),
            "impact_level": check.get("impact"),
            "current_status": current_status,
            "affected_entities_count": affected_entities_count,
            "affected_scope": affected_scope,
            "affected_entities_detail": affected_entities_detail,
            "account_id": account_id,
            "account_name": account_name_by_id.get(account_id, ""),
            "integration_id": (
                integration_obj.get("id")
                or check.get("integration_id")
                or check.get("Integration_id")
            ),
            "integration_name": (
                integration_obj.get("name")
                or check.get("integration_name")
                or check.get("saas_name")
            ),
            "integration_alias": (
                integration_obj.get("alias") or check.get("integration_alias")
            ),
            "security_check_id": security_check_id,
            "alert_id": alert_id,
            "alert_type": normalize_alert_type(
                alert.get("alert_type") or alert.get("type")
            ),
            "source": alert.get("source"),
            "source_id": source_id,
            "is_archived": bool(alert.get("is_archived")),
            "ticket_number": None,
            "ticket_owner": None,
            "ticket_status": None,
            "ticket_last_update_datetime": None,
            "ticket_last_update_content": None,
            "extracted_at_utc": extracted_at,
        }
        rows.append(row)

    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)


def _to_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def _fallback_status_from_alert(alert: dict[str, Any]) -> str:
    normalized = normalize_alert_type(alert.get("alert_type") or alert.get("type"))
    if normalized == "integration_failure":
        return "Failed"
    if normalized == "configuration_drift":
        return "Drifted"
    if normalized == "check_degraded":
        return "Degraded"
    return ""
