"""Notebook contract tests for integration overview notebook."""

from __future__ import annotations

import json
import os
import re
import textwrap
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


def test_integration_overview_notebook_contract() -> None:
    notebook_path = Path(__file__).resolve().parents[1] / "notebooks" / "as_integrations_overview.ipynb"
    assert notebook_path.exists(), "Integration overview notebook is missing"

    notebook = json.loads(notebook_path.read_text())
    cells = notebook.get("cells", [])

    assert len(cells) == 12

    expected_heads = {
        0: "# Adaptive Shield Integrations Overview (MVP)",
        1: "# Cell 1: Standalone Initialization (imports + helpers + config)",
        2: "# Cell 2: API Client Initialization",
        3: "# Cell 3: Get Accounts",
        4: "# Cell 4: Fetch Integrations (paginated)",
        5: "# Cell 5: Fetch Full Security Checks (strict mode)",
        6: "# Cell 6: Fetch Affected Entities for Failed Checks",
        7: "# Cell 7: Persist Daily Snapshots (Parquet)",
        8: "# Cell 8: Build History View from Local Snapshots",
        9: "# Cell 9: Render Integrations Overview UI",
        10: "# Cell 10: ServiceNow Stub (empty by default)",
        11: "# Cell 11: Export Files + Logs",
    }

    for index, head in expected_heads.items():
        source = "".join(cells[index].get("source", ""))
        first_line = source.splitlines()[0] if source.splitlines() else ""
        assert first_line == head

    snow_cell = "".join(cells[10].get("source", ""))
    assert "snow_df = pd.DataFrame(columns=['integration_id', *SNOW_COLUMNS])" in snow_cell
    assert "ServiceNow integration is not implemented" in snow_cell


def _weekly_report_notebook_cells() -> list[dict[str, Any]]:
    notebook_path = Path(__file__).resolve().parents[1] / "notebooks" / "as_weekly_report.ipynb"
    assert notebook_path.exists(), "Weekly report notebook is missing"

    notebook = json.loads(notebook_path.read_text())
    return notebook.get("cells", [])


def _exec_weekly_report_mapping_cell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    cells = _weekly_report_notebook_cells()
    mapping_cell = "".join(cells[4].get("source", ""))
    mapping_path = tmp_path / "config" / "snow_draft_assignment_mapping.csv"
    monkeypatch.setenv("SNOW_DRAFT_ASSIGNMENT_MAPPING_PATH", str(mapping_path))

    namespace: dict[str, Any] = {
        "Any": Any,
        "HTML": lambda value: value,
        "Path": Path,
        "ROOT_DIR": tmp_path,
        "display": lambda *args, **kwargs: None,
        "os": os,
        "pd": pd,
        "widgets": None,
    }
    exec(mapping_cell, namespace)
    return namespace


def _exec_weekly_report_draft_cell_definitions() -> dict[str, Any]:
    cells = _weekly_report_notebook_cells()
    draft_cell = "".join(cells[5].get("source", ""))
    draft_cell = draft_cell.rsplit("_snow_draft_render_ui()", 1)[0]

    namespace: dict[str, Any] = {
        "Any": Any,
        "HTML": lambda value: value,
        "Path": Path,
        "display": lambda *args, **kwargs: None,
        "json": json,
        "os": os,
        "pd": pd,
        "re": re,
        "textwrap": textwrap,
        "widgets": None,
    }
    exec(draft_cell, namespace)
    return namespace


def test_weekly_report_notebook_contract() -> None:
    cells = _weekly_report_notebook_cells()

    assert len(cells) == 7

    expected_heads = {
        0: "# Falcon SaaS Security Weekly Report",
        1: "# Cell 1: Standalone Initialization (bootstrap + functions + variables)",
        2: "# Cell 2: Unified Data Fetching + Processing (with stage progress)",
        3: "# Cell 3: Alerts UI (ServiceNow toggle)",
        4: "# Cell 4: ServiceNow Assignment Mapping Editor",
        5: "# Cell 5: ServiceNow Draft Incident Creator",
        6: "# Cell 6: Export Files",
    }

    for index, head in expected_heads.items():
        source = "".join(cells[index].get("source", ""))
        first_line = source.splitlines()[0] if source.splitlines() else ""
        assert first_line == head

    mapping_cell = "".join(cells[4].get("source", ""))
    assert "SNOW_DRAFT_SERVICENOW_INCIDENT_FIELDS" in mapping_cell
    assert "\"assignment_group\"" in mapping_cell
    assert "\"assigned_to\"" in mapping_cell


def test_service_now_mapping_editor_helpers_save_and_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = _exec_weekly_report_mapping_cell(tmp_path, monkeypatch)
    mapping_columns = namespace["SNOW_DRAFT_MAPPING_COLUMNS"]
    mapping_path = tmp_path / "config" / "snow_draft_assignment_mapping.csv"

    empty_df = namespace["_snow_mapping_load"](mapping_path)
    assert list(empty_df.columns) == mapping_columns
    assert empty_df.empty

    first_df = namespace["_snow_mapping_upsert"](
        empty_df,
        {
            "match_field": "integration_name",
            "match_value": "UiPath",
            "assignment_group": "RPA Security Team",
            "assigned_to": "Jane Doe",
            "category": "Security",
            "subcategory": "Automation",
            "impact": "2",
            "urgency": "2",
            "notes": "Route UiPath alerts to RPA owner",
        },
    )
    saved_df = namespace["_snow_mapping_save"](mapping_path, first_df)

    assert mapping_path.exists()
    assert mapping_path.read_text().splitlines()[0] == ",".join(mapping_columns)
    assert len(saved_df) == 1
    assert namespace["snow_draft_assignment_mapping_df"].equals(saved_df)

    updated_df = namespace["_snow_mapping_upsert"](
        saved_df,
        {
            "match_field": "integration_name",
            "match_value": "uipath",
            "assignment_group": "Automation Security",
            "assigned_to": "Jane Doe",
        },
    )

    assert len(updated_df) == 1
    assert updated_df.loc[0, "assignment_group"] == "Automation Security"
    assert updated_df.loc[0, "match_value"] == "uipath"

    with pytest.raises(ValueError, match="match_field"):
        namespace["_snow_mapping_upsert"](
            updated_df,
            {"match_field": "ticket_number", "match_value": "INC001"},
        )


def test_service_now_mapping_editor_fields_and_first_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = _exec_weekly_report_mapping_cell(tmp_path, monkeypatch)

    assert namespace["SNOW_DRAFT_SERVICENOW_INCIDENT_FIELDS"] == [
        "caller_id",
        "assignment_group",
        "assigned_to",
        "category",
        "subcategory",
        "impact",
        "urgency",
    ]

    mapping_df = pd.DataFrame(
        [
            {
                "match_field": "integration_name",
                "match_value": "Slack",
                "assignment_group": "First Team",
                "assigned_to": "First Owner",
            },
            {
                "match_field": "integration_name",
                "match_value": "Slack Enterprise",
                "assignment_group": "Second Team",
                "assigned_to": "Second Owner",
            },
        ]
    )

    assignment = namespace["_snow_mapping_assignment_for_row"](
        {"integration_name": "Slack Enterprise Grid"},
        mapping_df,
        {"caller_id": "David Shih", "assignment_group": "Default Team"},
    )

    assert assignment["caller_id"] == "David Shih"
    assert assignment["assignment_group"] == "First Team"
    assert assignment["assigned_to"] == "First Owner"

def test_falcon_servicenow_defaults_and_guides_use_falcon_copy() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env_example = (project_root / ".env.example").read_text()

    assert "API_SOURCE=falcon" in env_example
    assert "SNOW_INCIDENT_QUERY=short_descriptionLIKEFalcon Shield" in env_example
    assert "SNOW_INCIDENT_QUERY=short_descriptionLIKEAdaptiveShield" not in env_example

    cells = _weekly_report_notebook_cells()
    intro_cell = "".join(cells[0].get("source", ""))
    init_cell = "".join(cells[1].get("source", ""))
    draft_cell = "".join(cells[5].get("source", ""))

    assert "# Falcon SaaS Security Weekly Report" in intro_cell
    assert "CrowdStrike Falcon SaaS Security" in intro_cell
    assert "ServiceNow enrichment can be enabled with Falcon Shield incident mapping." in intro_cell
    assert 'SNOW_DEFAULT_INCIDENT_QUERY = "short_descriptionLIKEFalcon Shield"' in init_cell
    assert 'os.getenv("SNOW_INCIDENT_QUERY", SNOW_DEFAULT_INCIDENT_QUERY)' in init_cell
    assert 'base_query = _safe_text(config.get("snow_incident_query")) or SNOW_DEFAULT_INCIDENT_QUERY' in init_cell
    assert "is_snow_weekly_report_short_description(short_description)" in init_cell
    assert "short_descriptionLIKEAdaptiveShield" not in init_cell
    assert "Adaptive Shield Incident Draft" not in draft_cell
    assert "Adaptive Shield alert requires ServiceNow incident review." not in draft_cell

    for guide_path in [
        project_root / "docs" / "as_weekly_report_falcon_saas_security.html",
        project_root / "notebooks" / "as_weekly_report_falcon_saas_security.html",
    ]:
        guide = guide_path.read_text()
        assert "Falcon Shield &lt;Alert Type&gt;: [&lt;integration_alias&gt;] &lt;security_check_name&gt;" in guide
        assert "Adaptive Shield &lt;Alert Type&gt;: [&lt;integration_alias&gt;] &lt;security_check_name&gt;" not in guide


def test_service_now_short_description_parser_accepts_falcon_prefixes() -> None:
    init_cell = "".join(_weekly_report_notebook_cells()[1].get("source", ""))
    relevant = init_cell[init_cell.index("def normalize_match_text") : init_cell.index("def _fallback_match_key")]
    namespace: dict[str, Any] = {"Any": Any, "re": re}
    exec(relevant, namespace)

    assert namespace["is_snow_weekly_report_short_description"]("Falcon Shield Configuration Drift: [Slack] MFA")
    assert namespace["is_snow_weekly_report_short_description"]("Falcon SaaS Security saas: Slack | alias: SlackProd | check: MFA")
    assert namespace["is_snow_weekly_report_short_description"]("AdaptiveShield saas: Slack | alias: SlackProd | check: MFA")
    assert not namespace["is_snow_weekly_report_short_description"]("Random incident")
    assert namespace["parse_short_description_key"]("Falcon Shield SaaS | SlackProd | MFA required") == "saas | slackprod | mfa required"
    assert namespace["parse_short_description_key"]("Falcon SaaS Security saas: Slack | alias: SlackProd | check: MFA required") == "slack | slackprod | mfa required"


def test_service_now_draft_payload_uses_falcon_copy() -> None:
    namespace = _exec_weekly_report_draft_cell_definitions()
    payload = namespace["_snow_draft_payload"](
        {
            "alert_id": "alert-1",
            "alert_type": "configuration_drift",
            "account_name": "Primary",
            "account_id": "cid-1",
            "integration_name": "Slack Enterprise",
            "integration_alias": "Slack",
            "saas_name": "Slack",
            "security_check_name": "MFA required",
            "security_check_api_link": "https://falcon.example/checks/1",
            "impact_level": "High",
            "current_status": "open",
            "affected_scope": "entity",
            "affected_entities_count": 3,
            "change_datetime": "2026-07-02T00:00:00Z",
        },
        {"impact": "2", "urgency": "2", "category": "Security"},
    )

    assert payload["short_description"] == "Falcon Shield Configuration Drift: [Slack] MFA required"
    assert "Falcon Shield alert requires ServiceNow incident review." in payload["description"]
    assert "Falcon Shield Incident Draft" in payload["work_notes"]
    assert "Falcon Shield" in payload["work_notes"]
    assert "Adaptive Shield" not in payload["short_description"]
    assert "Adaptive Shield" not in payload["description"]
    assert "Adaptive Shield" not in payload["work_notes"]


def test_service_now_draft_candidates_merge_and_disable_groups() -> None:
    namespace = _exec_weekly_report_draft_cell_definitions()
    summary_df = pd.DataFrame(
        [
            {
                "alert_id": "old-slack",
                "alert_type": "configuration_drift",
                "account_id": "acct-1",
                "account_name": "Primary",
                "integration_id": "int-slack",
                "integration_name": "Slack Enterprise",
                "integration_alias": "Slack",
                "security_check_id": "check-mfa",
                "security_check_name": "MFA required",
                "impact_level": "Medium",
                "current_status": "Failed",
                "affected_entities_count": 1,
                "change_datetime": "2026-07-01T00:00:00Z",
            },
            {
                "alert_id": "new-slack",
                "alert_type": "configuration_drift",
                "account_id": "acct-1",
                "account_name": "Primary",
                "integration_id": "int-slack",
                "integration_name": "Slack Enterprise",
                "integration_alias": "Slack",
                "security_check_id": "check-mfa",
                "security_check_name": "MFA required",
                "impact_level": "High",
                "current_status": "Failed",
                "affected_entities_count": 3,
                "change_datetime": "2026-07-03T00:00:00Z",
            },
            {
                "alert_id": "mapped-box",
                "alert_type": "integration_failure",
                "account_id": "acct-1",
                "account_name": "Primary",
                "integration_id": "int-box",
                "integration_name": "Box",
                "security_check_id": "check-conn",
                "security_check_name": "Connection healthy",
                "impact_level": "High",
                "current_status": "Failed",
                "open_ticket_count_for_check": 1,
                "ticket_number": "INC001",
                "ticket_match_key": "box | connection healthy",
                "change_datetime": "2026-07-02T00:00:00Z",
            },
            {
                "alert_id": "passed-zoom",
                "alert_type": "configuration_drift",
                "account_id": "acct-1",
                "account_name": "Primary",
                "integration_id": "int-zoom",
                "integration_name": "Zoom",
                "security_check_id": "check-recording",
                "security_check_name": "Recording policy",
                "impact_level": "Low",
                "current_status": " Passed ",
                "change_datetime": "2026-07-04T00:00:00Z",
            },
        ]
    )

    candidates_df = namespace["_snow_draft_missing_ticket_candidates"](summary_df)
    candidates_df = namespace["_snow_draft_candidates_with_hidden_state"](
        candidates_df,
        {"hidden_keys": {}},
    )
    grouped_df = namespace["_snow_draft_grouped_candidates_df"](candidates_df)

    assert len(grouped_df) == 3

    slack_group = grouped_df[grouped_df["integration_name"] == "Slack Enterprise"].iloc[0]
    assert slack_group["alert_id"] == "new-slack"
    assert slack_group["snow_draft_duplicate_count"] == 2
    assert bool(slack_group["snow_draft_is_high_impact"]) is True
    assert bool(slack_group["snow_draft_is_disabled"]) is False

    mapped_group = grouped_df[grouped_df["integration_name"] == "Box"].iloc[0]
    assert bool(mapped_group["snow_draft_is_disabled"]) is True
    assert bool(mapped_group["snow_draft_is_servicenow_mapped"]) is True
    assert "ServiceNow" in mapped_group["snow_draft_disabled_reason"]
    assert "INC001" in mapped_group["snow_draft_disabled_reason"]

    passed_group = grouped_df[grouped_df["integration_name"] == "Zoom"].iloc[0]
    assert bool(passed_group["snow_draft_is_disabled"]) is True
    assert bool(passed_group["snow_draft_is_passed_configuration_drift"]) is True
    assert passed_group["snow_draft_disabled_reason"] == "Configuration drift is Passed"


def test_service_now_draft_candidates_sort_by_latest_alert_date_then_priority() -> None:
    namespace = _exec_weekly_report_draft_cell_definitions()
    summary_df = pd.DataFrame(
        [
            {
                "alert_id": "same-day-failure",
                "alert_type": "integration_failure",
                "account_id": "acct-1",
                "integration_id": "int-a",
                "integration_name": "A",
                "security_check_id": "check-a",
                "security_check_name": "A check",
                "impact_level": "Medium",
                "change_datetime": "2026-07-02T00:00:00Z",
            },
            {
                "alert_id": "latest-low",
                "alert_type": "configuration_drift",
                "account_id": "acct-1",
                "integration_id": "int-b",
                "integration_name": "B",
                "security_check_id": "check-b",
                "security_check_name": "B check",
                "impact_level": "Low",
                "change_datetime": "2026-07-03T00:00:00Z",
            },
            {
                "alert_id": "same-day-high",
                "alert_type": "configuration_drift",
                "account_id": "acct-1",
                "integration_id": "int-c",
                "integration_name": "C",
                "security_check_id": "check-c",
                "security_check_name": "C check",
                "impact_level": "High",
                "change_datetime": "2026-07-02T00:00:00Z",
            },
            {
                "alert_id": "missing-date",
                "alert_type": "configuration_drift",
                "account_id": "acct-1",
                "integration_id": "int-d",
                "integration_name": "D",
                "security_check_id": "check-d",
                "security_check_name": "D check",
                "impact_level": "High",
                "change_datetime": "",
            },
        ]
    )

    candidates_df = namespace["_snow_draft_candidates_with_hidden_state"](
        namespace["_snow_draft_missing_ticket_candidates"](summary_df),
        {"hidden_keys": {}},
    )
    grouped_df = namespace["_snow_draft_grouped_candidates_df"](candidates_df)

    assert grouped_df["alert_id"].tolist() == [
        "latest-low",
        "same-day-high",
        "same-day-failure",
        "missing-date",
    ]


def test_service_now_draft_raw_table_is_collapsed_by_default() -> None:
    namespace = _exec_weekly_report_draft_cell_definitions()
    html = namespace["_snow_draft_raw_table_html"](
        pd.DataFrame([{"integration_name": "Slack", "security_check_name": "MFA"}])
    )
    draft_cell = "".join(_weekly_report_notebook_cells()[5].get("source", ""))

    assert "<details class='snow-draft-raw-table'" in html
    assert "<details class='snow-draft-raw-table' open" not in html
    assert "raw_table_accordion.selected_index = None" in draft_cell
