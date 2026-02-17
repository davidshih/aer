"""Notebook contract tests for integration overview notebook."""

from __future__ import annotations

import json
from pathlib import Path


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
