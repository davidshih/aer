import html
import json
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

    def _load_stage7_text_renderer(self):
        source = self.cell_source(4)
        lines = source.splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("def _stage7_normalize_text"))
        end = next(i for i, line in enumerate(lines[start:], start) if line.startswith("def _stage7_candidate_defaults_paths"))
        chunk = "\n".join(lines[start:end])
        namespace = {"re": re, "html": html}
        exec(chunk, namespace)
        return namespace["_stage7_text_to_html"]


if __name__ == "__main__":
    unittest.main()
