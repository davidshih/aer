import ast
import glob
import io
import json
import os
from datetime import datetime as real_datetime
from pathlib import Path

import pandas as pd


NOTEBOOK_PATH = Path(__file__).resolve().parents[1] / "aer_user_listing.json"


def _load_code_source():
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell.get("cell_type") == "code"]
    return "\n\n".join("".join(cell.get("source", [])) for cell in code_cells)


def _load_namespace(*function_names):
    source = _load_code_source()
    tree = ast.parse(source, filename=str(NOTEBOOK_PATH))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in set(function_names)
    ]

    module = ast.Module(body=selected, type_ignores=[])
    namespace = {
        "glob": glob,
        "io": io,
        "os": os,
        "pd": pd,
        "datetime": real_datetime,
    }
    exec(compile(module, str(NOTEBOOK_PATH), "exec"), namespace)
    return namespace


def test_read_table_from_source_supports_uploaded_xlsx():
    namespace = _load_namespace("read_table_from_source")
    read_table_from_source = namespace["read_table_from_source"]

    expected = pd.DataFrame(
        {
            "department": ["Finance", "IT"],
            "reviewer": ["alice@example.com", "bob@example.com"],
        }
    )

    buffer = io.BytesIO()
    expected.to_excel(buffer, index=False)
    buffer.seek(0)

    actual = read_table_from_source("dept_mapping.xlsx", buffer)

    pd.testing.assert_frame_equal(actual, expected)


def test_get_latest_mapping_prefers_supported_dept_workbooks(tmp_path):
    namespace = _load_namespace("get_latest_mapping")
    get_latest_mapping = namespace["get_latest_mapping"]
    namespace["MAPPING_DIR"] = str(tmp_path)

    fallback = tmp_path / "mapping.csv"
    fallback.write_text("department,reviewer\nOps,ops@example.com\n", encoding="utf-8")
    os.utime(fallback, (2_000_000_000, 2_000_000_000))

    preferred = tmp_path / "dept_reviewers.xlsx"
    pd.DataFrame({"department": ["Finance"], "reviewer": ["fin@example.com"]}).to_excel(preferred, index=False)
    os.utime(preferred, (1_000_000_000, 1_000_000_000))

    assert get_latest_mapping() == str(preferred)


def test_build_stage2_output_path_avoids_same_second_collision(tmp_path):
    namespace = _load_namespace("build_stage2_output_path")

    class FixedDateTime:
        @classmethod
        def now(cls):
            return real_datetime(2026, 3, 12, 9, 15, 30)

    namespace["datetime"] = FixedDateTime
    build_stage2_output_path = namespace["build_stage2_output_path"]

    first_path = tmp_path / "input_file_validated_20260312_091530.xlsx"
    first_path.write_text("lock", encoding="utf-8")

    actual = build_stage2_output_path("input_file.xlsx", str(tmp_path))

    assert actual == str(tmp_path / "input_file_validated_20260312_091530_01.xlsx")

