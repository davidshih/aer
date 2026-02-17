"""Export helpers for weekly report artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def export_all(
    summary_df: pd.DataFrame | None,
    entities_df: pd.DataFrame | None,
    errors_df: pd.DataFrame | None,
    output_dir: str,
    ts: str,
    *,
    export_xlsx: bool = True,
    export_csv: bool = True,
) -> dict[str, str]:
    """Export summary, entities, and errors to XLSX and CSV files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    summary_df = summary_df if summary_df is not None else pd.DataFrame()
    entities_df = entities_df if entities_df is not None else pd.DataFrame()
    errors_df = errors_df if errors_df is not None else pd.DataFrame()

    results: dict[str, Any] = {
        "xlsx_path": "",
        "summary_csv_path": "",
        "entities_csv_path": "",
        "errors_csv_path": "",
    }

    if export_xlsx:
        xlsx_path = output_path / f"AS_Weekly_Report_{ts}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="summary", index=False)
            entities_df.to_excel(writer, sheet_name="entities", index=False)
            errors_df.to_excel(writer, sheet_name="errors", index=False)
        results["xlsx_path"] = str(xlsx_path)

    if export_csv:
        summary_csv_path = output_path / f"AS_Weekly_Summary_{ts}.csv"
        entities_csv_path = output_path / f"AS_Weekly_Entities_{ts}.csv"
        errors_csv_path = output_path / f"AS_Weekly_Errors_{ts}.csv"

        summary_df.to_csv(summary_csv_path, index=False)
        entities_df.to_csv(entities_csv_path, index=False)
        errors_df.to_csv(errors_csv_path, index=False)

        results["summary_csv_path"] = str(summary_csv_path)
        results["entities_csv_path"] = str(entities_csv_path)
        results["errors_csv_path"] = str(errors_csv_path)

    return {k: str(v) for k, v in results.items()}
