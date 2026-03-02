#!/usr/bin/env python3
"""Assemble AER notebook from individual cell Python files."""

import json
import os
import sys

CELL_FILES = [
    ("cell_1_ad_auth.py", "code", "Cell 1: Stage 1 — AD Authentication & User Download"),
    ("cell_15_org_tree.py", "code", "Cell 1.5: Stage 1.5 — Org Tree Builder"),
    ("cell_2_validation.py", "code", "Cell 2: Stage 2 — Email/User Validation"),
    ("cell_3_reviewer.py", "code", "Cell 3: Stage 3 — Reviewer Assignment"),
    ("cell_4_splitter.py", "code", "Cell 4: Stage 4 — Reviewer Splitter (Win COM)"),
    ("cell_5_spo_sync.py", "code", "Cell 5: Stage 5 — SharePoint Sync + Grant Edit"),
    ("cell_6_report.py", "code", "Cell 6: Stage 6 — Report Scanner & Dashboard"),
    ("cell_7_email.py", "code", "Cell 7: Stage 7 — Email Notification Center"),
]

CELL0_BOOTSTRAP = """# === CELL 0: Common Library & Configuration ===
# Thin bootstrap that loads the shared runtime module.

from pathlib import Path
import sys

_repo_root = Path.cwd().resolve()
_source_dir = _repo_root / "source"
if not _source_dir.exists():
    raise RuntimeError("Expected 'source/' next to the notebook. Open the notebook from the REVIEW workspace root.")
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from source import cell_0_common as aer_common

app_runtime = aer_common.build_runtime()
aer_common._inject_notebook_globals(globals(), app_runtime)

for _line in aer_common.runtime_status_lines(app_runtime):
    print(_line)
"""

MARKDOWN_HEADER = """# AER — Access Entitlement Review Suite v5.0

**Unified notebook** combining user listing creation (Stages 1-5) and report/notification (Stages 6-7).

## Improvements over v4.x
- **Unified Auth**: Single login, token auto-refresh across all stages
- **Shared Library**: Common helpers (Cell 0) eliminate code duplication
- **Rate Limiting**: All Graph/SPO API calls have exponential backoff + 429 retry
- **Checkpoint/Resume**: Stage 5 sync and Stage 7 email batch resume after interruption
- **Cross-Period Diff**: Stage 2 marks NEW/DEPARTED/CHANGED users vs previous cache
- **Mapping Version Control**: Stage 1.5 tracks all mapping changes with audit log
- **Atomic Cache**: Report cache writes are crash-safe (write-to-tmp then rename)
- **AD Cache Shared**: Stage 7 email lookup uses local AD cache (no per-reviewer API calls)
- **Configurable**: Year, fuzzy threshold, org root, email footer all from `.env`

## Cell Structure
| Cell | Stage | Purpose |
|------|-------|---------|
| 0 | — | Common Library (config, logger, HTTP, token, AD cache, SP helpers) |
| 1 | 1 | AD Authentication & User Download |
| 1.5 | 1.5 | Org Tree Builder & Mapping |
| 2 | 2 | Email/User Validation |
| 3 | 3 | Reviewer Assignment |
| 4 | 4 | Reviewer Splitter (Windows COM) |
| 5 | 5 | SharePoint Sync + Grant Edit |
| 6 | 6 | Report Scanner & Dashboard |
| 7 | 7 | Email Notification Center |

## File Structure
```
REVIEW/
├── aer_0302.json           # This notebook
├── input/
│   ├── ad_cache/           # AD user cache CSVs
│   └── mapping/            # Org mapping files (versioned)
└── output/YYYY-MM-DD/
    ├── logs/               # Unified log files
    ├── ad_cache/           # Output AD cache copy
    ├── orgchart/           # Org tree artifacts
    ├── stage2_validated/   # Validation results
    ├── stage3_review/      # Review workbooks
    ├── stage4_splitter/    # Per-reviewer folders
    ├── report/             # Report Excel files
    ├── cache/              # JSON caches (atomic)
    └── checkpoints/        # Resume checkpoints
```
"""

def read_cell(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def make_code_cell(source):
    lines = source.split("\n")
    source_lines = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            source_lines.append(line + "\n")
        else:
            if line:  # don't add empty trailing line
                source_lines.append(line)
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source_lines,
    }

def make_markdown_cell(source):
    lines = source.split("\n")
    source_lines = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            source_lines.append(line + "\n")
        else:
            if line:
                source_lines.append(line)
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source_lines,
    }

def main():
    cells_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/davidshih/projects/work/aer/REVIEW/aer_0302.json"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cells = []

    # Add markdown header
    cells.append(make_markdown_cell(MARKDOWN_HEADER.strip()))

    # Add bootstrap cell
    cells.append(make_code_cell(CELL0_BOOTSTRAP.strip()))
    print("  Added: bootstrap cell_0_common (thin runtime loader)")

    # Add stage code cells
    for filename, cell_type, title in CELL_FILES:
        filepath = os.path.join(cells_dir, filename)
        if not os.path.exists(filepath):
            print(f"WARNING: {filepath} not found, skipping")
            continue
        source = read_cell(filepath)
        cells.append(make_code_cell(source))
        print(f"  Added: {filename} ({len(source)} chars)")

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbformat_minor": 4,
                "pygments_lexer": "ipython3",
                "version": "3.8.5",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Notebook created: {output_path}")
    print(f"   Cells: {len(cells)} ({len(cells)-1} code + 1 markdown)")

    # Verify
    with open(output_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    print(f"   Verified: {len(nb['cells'])} cells, valid JSON")

    # Count total lines
    total_lines = sum(len(c.get("source", [])) for c in nb["cells"])
    print(f"   Total source lines: {total_lines}")

if __name__ == "__main__":
    main()
