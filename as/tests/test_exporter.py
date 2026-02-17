"""Unit tests for exporter module."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from as_weekly_report.exporter import export_all


def test_export_all_csv_only(tmp_path: Path) -> None:
    summary_df = pd.DataFrame([{"alert_id": "a1", "current_status": "Failed"}])
    entities_df = pd.DataFrame([{"alert_id": "a1", "entity_name": "alice@example.com"}])
    errors_df = pd.DataFrame([{"stage": "test", "message": "none"}])

    output = export_all(
        summary_df=summary_df,
        entities_df=entities_df,
        errors_df=errors_df,
        output_dir=str(tmp_path),
        ts="20260217_120000",
        export_xlsx=False,
        export_csv=True,
    )

    assert output["xlsx_path"] == ""
    assert Path(output["summary_csv_path"]).exists()
    assert Path(output["entities_csv_path"]).exists()
    assert Path(output["errors_csv_path"]).exists()


def test_export_all_with_xlsx(tmp_path: Path) -> None:
    summary_df = pd.DataFrame([{"alert_id": "a2", "current_status": "Drifted"}])
    entities_df = pd.DataFrame([{"alert_id": "a2", "entity_name": "repo-1"}])
    errors_df = pd.DataFrame(columns=["stage", "message"])

    output = export_all(
        summary_df=summary_df,
        entities_df=entities_df,
        errors_df=errors_df,
        output_dir=str(tmp_path),
        ts="20260217_130000",
        export_xlsx=True,
        export_csv=False,
    )

    assert Path(output["xlsx_path"]).exists()
    assert output["summary_csv_path"] == ""
    assert output["entities_csv_path"] == ""
    assert output["errors_csv_path"] == ""
