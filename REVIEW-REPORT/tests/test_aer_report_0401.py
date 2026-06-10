import html
import json
import pandas as pd
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "aer_report_0401.ipynb"


class AerReport0401NotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))

    def cell_source(self, index):
        return "".join(self.notebook["cells"][index].get("source", []))

    def test_notebook_has_expected_shape(self):
        self.assertEqual(len(self.notebook["cells"]), 5)
        self.assertEqual(self.notebook["cells"][0]["cell_type"], "markdown")
        for index in [1, 2, 3, 4]:
            self.assertEqual(self.notebook["cells"][index]["cell_type"], "code")

    def test_code_cells_compile(self):
        for index in [1, 2, 3, 4]:
            compile(self.cell_source(index), f"cell_{index}", "exec")

    def test_cell1_keeps_graph_request_helpers(self):
        source = self.cell_source(1)
        self.assertIn("def _graph_request", source)
        self.assertIn("def graph_get", source)
        self.assertIn("def graph_post", source)

    def test_cell2_keeps_pagination_support(self):
        source = self.cell_source(2)
        self.assertIn("def _graph_paginated_values", source)
        self.assertIn("@odata.nextLink", source)

    def test_stage7_mailto_anchor_is_preserved(self):
        render = self._load_stage7_text_renderer()
        rendered = render('Contact us: <a href="mailto:test@example.com">Email Team</a>')
        self.assertIn('<a href="mailto:test@example.com">Email Team</a>', rendered)

    def test_stage7_mailto_common_typo_is_tolerated(self):
        render = self._load_stage7_text_renderer()
        rendered = render('Contact us: <a herf="mailto:test2@example.com">Email Team 2</a>')
        self.assertIn('<a href="mailto:test2@example.com">Email Team 2</a>', rendered)

    def test_stage7_escapes_non_mailto_html(self):
        render = self._load_stage7_text_renderer()
        rendered = render("<b>unsafe</b>")
        self.assertIn("&lt;b&gt;unsafe&lt;/b&gt;", rendered)

    def test_stage7_email_rows_keep_pending_apps_with_missing_folder_url(self):
        prepare_rows = self._load_stage7_email_preparer()
        raw_df = pd.DataFrame([
            self._pending_row("infrastructure", "xxx1", "Reviewer One", "https://example/xxx1"),
            self._pending_row("infrastructure", "xxx2", "Reviewer One", None),
            self._pending_row("Q2", "xxxa", "Reviewer One", "https://example/xxxa"),
            self._pending_row("Q2", "xxxb", "Reviewer One", ""),
            self._completed_row("Q2", "done-app", "Reviewer One", "https://example/done"),
        ])

        rows = prepare_rows(
            raw_df,
            notes_db={},
            ad_email_set=set(),
            ad_name_map={},
            email_lookup_func=lambda reviewer, *_: "reviewer.one@example.com",
        )

        self.assertEqual(len(rows), 4)
        self.assertEqual(
            sorted((row["Category"], row["App_Name"]) for row in rows),
            [
                ("Q2", "xxxa"),
                ("Q2", "xxxb"),
                ("infrastructure", "xxx1"),
                ("infrastructure", "xxx2"),
            ],
        )
        self.assertEqual(
            {row["App_Name"]: row["folder_url"] for row in rows},
            {
                "xxx1": "https://example/xxx1",
                "xxx2": "#",
                "xxxa": "https://example/xxxa",
                "xxxb": "#",
            },
        )

    def test_stage7_email_rows_preserve_skip_rules(self):
        prepare_rows = self._load_stage7_email_preparer()
        raw_df = pd.DataFrame([
            self._pending_row("infrastructure", "xxx1", "Reviewer One", "https://example/xxx1"),
            self._pending_row("infrastructure", "xxx2", "Reviewer One", "https://example/xxx2"),
            self._pending_row("Q2", "xxxa", "Reviewer One", "https://example/xxxa"),
            self._pending_row("Q2", "xxxb", "Reviewer One", "https://example/xxxb"),
        ])
        notes_db = {
            "infrastructure > xxx2": {"app_status": "Force Completed"},
            "Q2 > xxxb": {"reviewers": {"Reviewer One": {"override": "Waived"}}},
        }

        rows = prepare_rows(
            raw_df,
            notes_db=notes_db,
            ad_email_set=set(),
            ad_name_map={},
            email_lookup_func=lambda reviewer, *_: "reviewer.one@example.com",
        )

        self.assertEqual(
            sorted((row["Category"], row["App_Name"]) for row in rows),
            [
                ("Q2", "xxxa"),
                ("infrastructure", "xxx1"),
            ],
        )

    def _load_stage7_text_renderer(self):
        source = self.cell_source(4)
        lines = source.splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("def _stage7_normalize_text"))
        end = next(i for i, line in enumerate(lines[start:], start) if line.startswith("def _stage7_candidate_defaults_paths"))
        chunk = "\n".join(lines[start:end])
        namespace = {"re": re, "html": html}
        exec(chunk, namespace)
        return namespace["_stage7_text_to_html"]

    def _load_stage7_email_preparer(self):
        source = self.cell_source(4)
        lines = source.splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("def _stage7_normalize_folder_url"))
        end = next(i for i, line in enumerate(lines[start:], start) if line.startswith("raw_df ="))
        chunk = "\n".join(lines[start:end])
        namespace = {
            "pd": pd,
            "fmt_date_long": lambda value: f"sent:{value}",
            "calc_due_date_long": lambda value: f"due:{value}",
        }
        exec(chunk, namespace)
        return namespace["_stage7_prepare_email_rows"]

    def _pending_row(self, category, app_name, reviewer, folder_url):
        return {
            "Category": category,
            "App_Name": app_name,
            "reviewer": reviewer,
            "folder_url": folder_url,
            "is_missing": True,
            "File_Created_Date": "2026-04-01T00:00:00Z",
        }

    def _completed_row(self, category, app_name, reviewer, folder_url):
        row = self._pending_row(category, app_name, reviewer, folder_url)
        row["is_missing"] = False
        return row


if __name__ == "__main__":
    unittest.main()
