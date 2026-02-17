"""Unit tests for transform helpers."""

from __future__ import annotations

import pandas as pd

from as_weekly_report.transform import (
    build_entities_df,
    build_summary_df,
    filter_target_alerts,
    normalize_alert_type,
)


def test_normalize_alert_type_variants() -> None:
    assert normalize_alert_type("Configuration Drift") == "configuration_drift"
    assert normalize_alert_type("integration-failure") == "integration_failure"
    assert normalize_alert_type("Security Check Degraded") == "check_degraded"


def test_filter_target_alerts_ignores_archived_and_degraded() -> None:
    rows = [
        {"id": "1", "alert_type": "configuration_drift", "is_archived": False},
        {"id": "2", "alert_type": "integration_failure", "is_archived": False},
        {"id": "3", "alert_type": "Security Check Degraded", "is_archived": False},
        {"id": "4", "alert_type": "configuration_drift", "is_archived": True},
    ]
    filtered = filter_target_alerts(rows)
    assert [item["id"] for item in filtered] == ["1", "2"]


def test_build_entities_df_maps_entity_columns() -> None:
    raw = [
        {
            "account_id": "acc-1",
            "alert_id": "alert-1",
            "security_check_id": "check-1",
            "entity": {
                "type": "user",
                "entity_name": "alice@example.com",
                "dismissed": False,
                "dismissed_reason": None,
                "dismiss_expiration_date": None,
                "extra_context": [{"role": "admin"}],
                "usage": {"last_access": "2026-02-16T00:00:00Z"},
            },
        }
    ]
    entities_df = build_entities_df(raw)

    assert len(entities_df) == 1
    assert entities_df.loc[0, "entity_type"] == "user"
    assert entities_df.loc[0, "entity_name"] == "alice@example.com"
    assert "role" in entities_df.loc[0, "entity_extra_context_json"]


def test_build_summary_df_sets_global_and_required_columns() -> None:
    alerts = [
        {
            "id": "alert-1",
            "account_id": "acc-1",
            "source": "security_checks",
            "source_id": "check-1",
            "alert_type": "configuration_drift",
            "timestamp": "2026-02-16T00:00:00Z",
            "is_archived": False,
            "integration": {"id": "int-1", "name": "Office 365", "alias": "Prod"},
        }
    ]
    checks = [
        {
            "alert_id": "alert-1",
            "account_id": "acc-1",
            "security_check_id": "check-1",
            "name": "Require MFA",
            "details": "MFA setting is disabled",
            "impact": "High",
            "status": "Failed",
            "remediation_plan": "Enable MFA in tenant policy",
            "is_global": True,
            "affected": "Global",
        }
    ]
    entities = []
    accounts = [{"id": "acc-1", "name": "Production"}]

    summary_df = build_summary_df(
        alerts=alerts,
        checks=checks,
        entities=entities,
        accounts=accounts,
        extracted_at_utc="2026-02-17T00:00:00Z",
    )

    assert len(summary_df) == 1
    assert summary_df.loc[0, "affected_scope"] == "global"
    assert summary_df.loc[0, "affected_entities_count"] == "global"
    assert summary_df.loc[0, "security_check_name"] == "Require MFA"
    assert summary_df.loc[0, "account_name"] == "Production"


def test_build_summary_df_fallback_status_for_integration_failure() -> None:
    alerts = [
        {
            "id": "alert-2",
            "account_id": "acc-2",
            "source": "security_checks",
            "source_id": "check-2",
            "alert_type": "integration_failure",
            "timestamp": "2026-02-16T10:00:00Z",
            "is_archived": False,
            "integration": {"id": "int-2", "name": "Slack", "alias": "Corp Slack"},
        }
    ]
    checks = [
        {
            "alert_id": "alert-2",
            "account_id": "acc-2",
            "security_check_id": "check-2",
            "name": "Integration Access Token",
            "details": "Token refresh failed",
            "impact": "Medium",
            "status": None,
            "remediation_plan": "Re-authorize integration",
            "is_global": False,
            "affected": None,
        }
    ]
    entities = build_entities_df(
        [
            {
                "alert_id": "alert-2",
                "account_id": "acc-2",
                "security_check_id": "check-2",
                "entity": {"type": "user", "entity_name": "john@example.com"},
            },
            {
                "alert_id": "alert-2",
                "account_id": "acc-2",
                "security_check_id": "check-2",
                "entity": {"type": "user", "entity_name": "mary@example.com"},
            },
        ]
    )

    summary_df = build_summary_df(
        alerts=alerts,
        checks=checks,
        entities=entities.to_dict("records"),
        accounts=[{"id": "acc-2", "name": "Staging"}],
    )

    assert isinstance(summary_df, pd.DataFrame)
    assert summary_df.loc[0, "current_status"] == "Failed"
    assert summary_df.loc[0, "affected_scope"] == "entity"
    assert summary_df.loc[0, "affected_entities_count"] == 2
    assert "john@example.com" in summary_df.loc[0, "affected_entities_detail"]
