from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_notebook_executes_end_to_end(sample_flow_zip_path: Path, tmp_path: Path, monkeypatch) -> None:
    notebook_path = PROJECT_ROOT / "powerdocu_notebook.ipynb"
    output_dir = tmp_path / "notebook-output"

    monkeypatch.setenv("POWERDOCU_NOTEBOOK_SAMPLE_INPUT", str(sample_flow_zip_path))
    monkeypatch.setenv("POWERDOCU_NOTEBOOK_OUTPUT_DIR", str(output_dir))

    with notebook_path.open(encoding="utf-8") as handle:
        notebook = nbformat.read(handle, as_version=4)

    client = NotebookClient(notebook, timeout=120, kernel_name="python3")
    client.execute(cwd=str(PROJECT_ROOT))

    assert (output_dir / "FlowDoc-Sample-Flow" / "index-Sample-Flow.md").exists()
    assert (output_dir / "FlowDoc-Sample-Flow" / "flow-overview.mmd").exists()
