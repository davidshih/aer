"""Notebook contract tests for integration overview notebook."""

from __future__ import annotations

import json
import os
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


def test_weekly_report_notebook_contract() -> None:
    cells = _weekly_report_notebook_cells()

    assert len(cells) == 7

    expected_heads = {
        0: "# Adaptive Shield Weekly Report (MVP)",
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
