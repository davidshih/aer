#!/usr/bin/env python3
"""Headless Snowflake security-check runner for cron jobs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Optional


PROJECT_DIR = Path(__file__).resolve().parent
NOTEBOOK_FILENAME = "snowflake_trust_center_to_secops.ipynb"
HELPER_CELL_PREFIX = "# Cell 2 - Helpers and configuration"
ALL_SELECTION = "all"


class DailyRunnerError(Exception):
    """Raised when the daily runner must stop with a non-zero exit."""

    def __init__(self, message: str, summary: Optional[dict] = None):
        super().__init__(message)
        self.summary = summary or {}


def load_notebook_helpers(project_dir: Path = PROJECT_DIR) -> dict:
    """Load the notebook's non-UI helper cell into an isolated namespace."""
    notebook_path = project_dir / NOTEBOOK_FILENAME
    with notebook_path.open(encoding="utf-8") as fh:
        notebook = json.load(fh)

    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if source.lstrip().startswith(HELPER_CELL_PREFIX):
            namespace = {"__NOTEBOOK_TEST__": True}
            exec(source, namespace)
            return namespace

    raise DailyRunnerError(
        f"Could not find notebook helper cell starting with: {HELPER_CELL_PREFIX}"
    )


def parse_selection(raw_value: str, setting_name: str) -> list[str]:
    """Parse a required comma-separated selection from the environment."""
    values = [item.strip() for item in (raw_value or "").split(",") if item.strip()]
    if not values:
        raise DailyRunnerError(f"{setting_name} is required for the daily runner.")

    normalized = [value.lower() for value in values]
    if ALL_SELECTION in normalized and len(values) > 1:
        raise DailyRunnerError(f"{setting_name}=all must be used by itself.")
    return values


def expand_selection(
    requested_values: list[str],
    available_values: list[str],
    setting_name: str,
) -> list[str]:
    """Expand `all` and validate selected values against known config keys."""
    if len(requested_values) == 1 and requested_values[0].lower() == ALL_SELECTION:
        return list(available_values)

    invalid = sorted(set(requested_values) - set(available_values))
    if invalid:
        raise DailyRunnerError(
            f"Unknown {setting_name} value(s): {invalid}. Available: {available_values}"
        )

    requested = set(requested_values)
    return [value for value in available_values if value in requested]


def resolve_selected_groups(config: dict, environ: Mapping[str, str], helpers: dict) -> dict:
    """Resolve env-selected accounts and checks to normalized group keys."""
    group_catalog = helpers["build_group_catalog"](config)
    account_labels = [account["label"] for account in group_catalog["accounts"]]
    check_keys = [check["key"] for check in group_catalog["queries"]]

    selected_accounts = expand_selection(
        parse_selection(environ.get("SELECTED_ACCOUNTS", ""), "SELECTED_ACCOUNTS"),
        account_labels,
        "SELECTED_ACCOUNTS",
    )
    selected_checks = expand_selection(
        parse_selection(environ.get("SELECTED_CHECKS", ""), "SELECTED_CHECKS"),
        check_keys,
        "SELECTED_CHECKS",
    )

    selected_account_set = set(selected_accounts)
    selected_check_set = set(selected_checks)
    selected_groups = [
        group_key
        for group_key in group_catalog["group_order"]
        if group_catalog["group_lookup"][group_key]["account_label"] in selected_account_set
        and group_catalog["group_lookup"][group_key]["query_key"] in selected_check_set
    ]

    if not selected_groups:
        raise DailyRunnerError("SELECTED_ACCOUNTS and SELECTED_CHECKS matched no groups.")

    return {
        "accounts": selected_accounts,
        "checks": selected_checks,
        "groups": helpers["normalize_group_keys"](group_catalog, selected_groups),
    }


def build_no_events_result(config: dict, helpers: dict) -> dict:
    """Build the skipped SecOps result used when every selected query is empty."""
    return {
        "sent": 0,
        "batches": 0,
        "attempted_batches": 0,
        "failed_batches": 0,
        "failed_event_count": 0,
        "planned_batches": 0,
        "planned_bytes": 0,
        "auth_mode": helpers["describe_auth_mode"](config["SECOPS_WEBHOOK_URL"]),
        "dry_run": config["DRY_RUN"],
        "skipped": True,
        "errors": [],
    }


def find_query_errors(query_results: dict, selected_groups: list[str]) -> list[dict]:
    """Return selected query result errors that should block SecOps delivery."""
    errors = []
    for group_key in selected_groups:
        result = query_results.get(group_key, {})
        if result.get("status") == "error":
            errors.append(
                {
                    "group_key": group_key,
                    "account_label": result.get("account_label"),
                    "query_key": result.get("query_key"),
                    "query_title": result.get("query_title"),
                    "error": result.get("error"),
                }
            )
    return errors


def build_summary(
    config: dict,
    helpers: dict,
    selection: dict,
    sanity_results: list[dict],
    query_results: dict,
    payload_plan: dict,
    secops_result: dict,
    status: str = "success",
) -> dict:
    """Build the cron-friendly JSON summary."""
    return {
        "status": status,
        "project_dir": config["PROJECT_DIR"],
        "env_path": config["ENV_PATH"],
        "env_found": config["ENV_FOUND"],
        "dry_run": config["DRY_RUN"],
        "selected_accounts": selection["accounts"],
        "selected_checks": selection["checks"],
        "selected_groups": selection["groups"],
        "sanity_checks": helpers["json_safe_value"](sanity_results),
        "query_results": helpers["json_safe_value"](
            helpers["summarize_query_results"](query_results)
        ),
        "payload_plan": helpers["json_safe_value"](payload_plan),
        "secops_result": helpers["json_safe_value"](secops_result),
    }


def execute_daily_run(
    config: dict,
    environ: Mapping[str, str],
    helpers: dict,
    connect_fn: Optional[Callable] = None,
    fetch_fn: Optional[Callable] = None,
    close_fn: Optional[Callable] = None,
    sanity_fn: Optional[Callable] = None,
    post_fn: Optional[Callable] = None,
) -> dict:
    """Execute selected checks and send resulting events when configured."""
    selection = resolve_selected_groups(config, environ, helpers)

    sanity_fn = sanity_fn or helpers["run_selected_account_sanity_checks"]
    sanity_results = sanity_fn(
        config,
        selection["accounts"],
        connect_fn=connect_fn,
        close_fn=close_fn,
    )

    query_results = helpers["execute_selected_groups"](
        config,
        selection["groups"],
        connect_fn=connect_fn,
        fetch_fn=fetch_fn,
        close_fn=close_fn,
    )

    payload_plan = {
        "selected_groups": [],
        "total_events": 0,
        "generated_at": None,
        "dry_run": config["DRY_RUN"],
    }
    secops_result = build_no_events_result(config, helpers)
    query_errors = find_query_errors(query_results, selection["groups"])
    if query_errors:
        summary = build_summary(
            config,
            helpers,
            selection,
            sanity_results,
            query_results,
            payload_plan,
            secops_result,
            status="error",
        )
        summary["query_errors"] = query_errors
        raise DailyRunnerError(
            "Selected query errors blocked SecOps delivery.",
            summary=summary,
        )

    events, payload_plan = helpers["build_selected_events"](
        query_results,
        selection["groups"],
        dry_run=config["DRY_RUN"],
    )

    if events:
        if post_fn is None:
            secops_result = helpers["send_to_secops"](events, config)
        else:
            secops_result = helpers["send_to_secops"](events, config, post_fn=post_fn)

    return build_summary(
        config,
        helpers,
        selection,
        sanity_results,
        query_results,
        payload_plan,
        secops_result,
    )


def load_config_from_env_file(env_path: Path, project_dir: Path, helpers: dict) -> dict:
    """Load dotenv values and build the existing notebook runtime config."""
    helpers["load_dotenv"](env_path, override=True)
    return helpers["build_runtime_config"](
        os.environ,
        project_dir=project_dir,
        env_path=env_path,
        prompt_for_missing=False,
    )


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run selected Snowflake security checks and send them to Google SecOps."
    )
    parser.add_argument(
        "--env",
        default=str(PROJECT_DIR / ".env"),
        help="Path to the .env config file. Defaults to ./.env next to this script.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    env_path = Path(args.env).expanduser().resolve()

    try:
        helpers = load_notebook_helpers(PROJECT_DIR)
        config = load_config_from_env_file(env_path, PROJECT_DIR, helpers)
        summary = execute_daily_run(config, os.environ, helpers)
    except DailyRunnerError as exc:
        summary = exc.summary or {"status": "error"}
        summary["error"] = str(exc)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "env_path": str(env_path),
                    "error": str(exc),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
