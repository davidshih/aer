import os
from decimal import Decimal
from pathlib import Path

import nbformat
import pandas as pd


NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[1] / "snowflake_trust_center_to_secops.ipynb"
)
HELPER_CELL_PREFIX = "# Cell 2 - Helpers and configuration"
CONTROL_PANEL_CELL_PREFIX = "# Cell 3 - Unified control panel"


def load_notebook():
    with NOTEBOOK_PATH.open(encoding="utf-8") as fh:
        return nbformat.read(fh, as_version=4)


def find_code_cell_source(notebook, prefix: str) -> str:
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        source = cell.source
        if source.lstrip().startswith(prefix):
            return source
    raise AssertionError(f"Could not find notebook cell starting with: {prefix}")


def load_helper_namespace():
    notebook = load_notebook()
    namespace = {"__NOTEBOOK_TEST__": True}
    exec(find_code_cell_source(notebook, HELPER_CELL_PREFIX), namespace)
    return namespace


def make_config(namespace):
    env = {
        "SNOWFLAKE_ACCOUNT_1": "prod-account.us-east-1",
        "SNOWFLAKE_USER_1": "svc_prod",
        "SNOWFLAKE_PRIVATE_KEY_PATH_1": "~/.snowflake/prod.p8",
        "SNOWFLAKE_LABEL_1": "prod",
        "SNOWFLAKE_ACCOUNT_3": "staging-account.eu-west-1",
        "SNOWFLAKE_USER_3": "svc_staging",
        "SNOWFLAKE_PRIVATE_KEY_PATH_3": "~/.snowflake/staging.p8",
        "SNOWFLAKE_LABEL_3": "staging",
        "SECURITY_CHECK_NAME_1": "users_without_mfa",
        "SECURITY_CHECK_SQL_1": "SELECT 1\\nAS one",
        "SECURITY_CHECK_SQL_4": "SELECT 4",
        "SECOPS_WEBHOOK_URL": "https://example.test/import?key=test-key&secret=test-secret",
        "BATCH_SIZE": "25",
        "DRY_RUN": "true",
    }
    return namespace["build_runtime_config"](
        env,
        project_dir=Path("/tmp/project"),
        env_path=Path("/tmp/project/.env"),
        prompt_for_missing=False,
    )


def make_success_result(namespace, group_key: str, row_count: int = 2):
    account_label, query_key = namespace["split_group_key"](group_key)
    return {
        "group_key": group_key,
        "account_label": account_label,
        "query_key": query_key,
        "query_name": query_key,
        "status": "success",
        "row_count": row_count,
        "columns": ["value"],
        "dataframe": pd.DataFrame([{"value": idx} for idx in range(1, row_count + 1)]),
        "error": None,
    }


def test_notebook_json_is_valid():
    notebook = load_notebook()
    nbformat.validate(notebook)


def test_notebook_is_consolidated_to_four_cells_with_control_panel():
    notebook = load_notebook()

    assert len(notebook.cells) == 4
    control_panel_source = find_code_cell_source(notebook, CONTROL_PANEL_CELL_PREFIX)
    assert "widgets.GridspecLayout" in control_panel_source
    assert 'description="DRY_RUN"' in control_panel_source
    assert 'description="Run Selected"' in control_panel_source
    assert 'description="Send Selected to SecOps"' in control_panel_source


def test_build_runtime_config_supports_sparse_indexes_and_multiline_sql():
    namespace = load_helper_namespace()
    config = make_config(namespace)

    assert [account["label"] for account in config["SNOWFLAKE_ACCOUNTS"]] == [
        "prod",
        "staging",
    ]
    assert [check["key"] for check in config["SECURITY_CHECKS"]] == [
        "security_check_1",
        "security_check_4",
    ]
    assert config["SECURITY_CHECKS"][0]["sql"] == "SELECT 1\nAS one"
    assert config["BATCH_SIZE"] == 25
    assert config["DRY_RUN"] is True


def test_build_runtime_config_accepts_separate_secops_header_auth_values():
    namespace = load_helper_namespace()
    env = {
        "SNOWFLAKE_ACCOUNT_1": "prod-account.us-east-1",
        "SNOWFLAKE_USER_1": "svc_prod",
        "SNOWFLAKE_PRIVATE_KEY_PATH_1": "~/.snowflake/prod.p8",
        "SNOWFLAKE_LABEL_1": "prod",
        "SECURITY_CHECK_SQL_1": "SELECT 1",
        "SECOPS_WEBHOOK_URL": "https://example.test/import",
        "SECOPS_API_KEY": "header-key",
        "SECOPS_WEBHOOK_SECRET": "header-secret",
        "DRY_RUN": "false",
    }

    config = namespace["build_runtime_config"](
        env,
        project_dir=Path("/tmp/project"),
        env_path=Path("/tmp/project/.env"),
        prompt_for_missing=False,
    )

    assert config["SECOPS_WEBHOOK_URL"] == "https://example.test/import"
    assert config["SECOPS_API_KEY"] == "header-key"
    assert config["SECOPS_WEBHOOK_SECRET"] == "header-secret"
    assert namespace["describe_auth_mode"](config["SECOPS_WEBHOOK_URL"]) == "headers"


def test_load_environment_overrides_existing_secops_values_from_dotenv(tmp_path, monkeypatch):
    namespace = load_helper_namespace()
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SECOPS_API_KEY=file-key\n"
        "SECOPS_WEBHOOK_SECRET=file-secret\n"
        "SECOPS_WEBHOOK_URL=https://example.test/import\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("NOTEBOOK_ROOT", str(tmp_path))
    monkeypatch.setenv("SECOPS_API_KEY", "stale-key")
    monkeypatch.setenv("SECOPS_WEBHOOK_SECRET", "stale-secret")
    monkeypatch.setenv("SECOPS_WEBHOOK_URL", "https://example.test/old")

    project_dir, resolved_env_path = namespace["load_environment"](env_path)

    assert project_dir == tmp_path.resolve()
    assert resolved_env_path == env_path.resolve()
    assert os.environ["SECOPS_API_KEY"] == "file-key"
    assert os.environ["SECOPS_WEBHOOK_SECRET"] == "file-secret"
    assert os.environ["SECOPS_WEBHOOK_URL"] == "https://example.test/import"


def test_create_app_state_seeds_dry_run_and_first_account_defaults():
    namespace = load_helper_namespace()
    config = make_config(namespace)

    app_state = namespace["create_app_state"](config)

    assert app_state["dry_run"] is True
    assert app_state["checked_groups"] == [
        "prod::security_check_1",
        "prod::security_check_4",
    ]
    assert config["SEND_SELECTION"] == app_state["checked_groups"]


def test_execute_selected_groups_only_runs_requested_pairs():
    namespace = load_helper_namespace()
    config = make_config(namespace)
    selected_group_keys = [
        namespace["make_group_key"]("prod", "security_check_4"),
        namespace["make_group_key"]("staging", "security_check_4"),
    ]
    connect_calls = []
    fetch_calls = []

    def fake_connect(account_cfg):
        connect_calls.append(account_cfg["label"])
        return {"label": account_cfg["label"]}

    def fake_fetch(conn, sql):
        fetch_calls.append((conn["label"], sql))
        return pd.DataFrame([{"account": conn["label"], "sql": sql}])

    results = namespace["execute_selected_groups"](
        config,
        selected_group_keys,
        connect_fn=fake_connect,
        fetch_fn=fake_fetch,
        close_fn=lambda _conn: None,
    )

    assert list(results) == selected_group_keys
    assert connect_calls == ["prod", "staging"]
    assert fetch_calls == [
        ("prod", "SELECT 4"),
        ("staging", "SELECT 4"),
    ]


def test_sync_runtime_selection_marks_mode_changes_dirty_after_run():
    namespace = load_helper_namespace()
    config = make_config(namespace)
    app_state = namespace["create_app_state"](config)
    app_state["last_run_selection"] = namespace["get_selection_snapshot"](
        app_state["checked_groups"],
        app_state["dry_run"],
        app_state["group_catalog"],
    )

    namespace["sync_runtime_selection"](
        app_state,
        app_state["checked_groups"],
        False,
    )

    assert app_state["selection_dirty"] is True
    assert "Mode changed" in app_state["dirty_reason"]


def test_reduce_send_state_requires_clean_successful_checked_groups():
    namespace = load_helper_namespace()
    config = make_config(namespace)
    app_state = namespace["create_app_state"](config)
    selected_group = app_state["checked_groups"][0]

    app_state["query_results"][selected_group] = make_success_result(namespace, selected_group)
    app_state["last_run_selection"] = namespace["get_selection_snapshot"](
        app_state["checked_groups"],
        app_state["dry_run"],
        app_state["group_catalog"],
    )
    app_state["selection_dirty"] = False
    app_state["dirty_reason"] = "Ready to send."

    ready_state = namespace["reduce_send_state"](app_state)
    assert ready_state["enabled"] is True
    assert ready_state["eligible_groups"] == [selected_group]

    app_state["selection_dirty"] = True
    app_state["dirty_reason"] = "Selection changed; rerun required before send."
    dirty_state = namespace["reduce_send_state"](app_state)
    assert dirty_state["enabled"] is False
    assert "rerun required" in dirty_state["reason"]


def test_build_sender_config_uses_runtime_dry_run_instead_of_env_default():
    namespace = load_helper_namespace()
    config = make_config(namespace)
    app_state = namespace["create_app_state"](config)
    app_state["dry_run"] = False

    sender_config = namespace["build_sender_config"](config, app_state)

    assert config["DRY_RUN"] is True
    assert sender_config["DRY_RUN"] is False


def test_build_header_snapshot_reflects_live_mode_and_send_state():
    namespace = load_helper_namespace()
    config = make_config(namespace)
    app_state = namespace["create_app_state"](config)
    selected_group = app_state["checked_groups"][0]

    app_state["dry_run"] = False
    app_state["query_results"][selected_group] = make_success_result(namespace, selected_group)
    app_state["last_run_selection"] = namespace["get_selection_snapshot"](
        app_state["checked_groups"],
        app_state["dry_run"],
        app_state["group_catalog"],
    )
    app_state["selection_dirty"] = False
    app_state["dirty_reason"] = "Ready to send."

    header = namespace["build_header_snapshot"](config, app_state)
    _events, payload_plan = namespace["build_selected_events"](
        app_state["query_results"],
        app_state["checked_groups"],
        dry_run=app_state["dry_run"],
    )

    assert header["dry_run"] is False
    assert header["send_enabled"] is True
    assert payload_plan["dry_run"] is False


def test_row_to_generic_log_serializes_payload_and_extracts_timestamp():
    namespace = load_helper_namespace()
    record = {
        "COMPLETED_AT": pd.Timestamp("2026-04-14T12:00:00Z"),
        "SEVERITY": "HIGH",
        "SCORE": Decimal("10.5"),
        "EMPTY": float("nan"),
    }

    event = namespace["row_to_generic_log"](
        record,
        account_label="prod",
        query_key="security_check_1",
        query_name="users_without_mfa",
        row_index=2,
        generated_at="2026-04-14T15:00:00+00:00",
    )

    assert event["snowflake_account"] == "prod"
    assert event["snowflake_query_key"] == "security_check_1"
    assert event["snowflake_query_name"] == "users_without_mfa"
    assert event["generated_at"] == "2026-04-14T15:00:00+00:00"
    assert event["row_index"] == 2
    assert event["source_timestamp"] == "2026-04-14T12:00:00+00:00"
    assert event["result"]["SCORE"] == 10.5
    assert event["result"]["EMPTY"] is None


def test_row_to_generic_log_handles_nat_without_astimezone_error():
    namespace = load_helper_namespace()
    record = {
        "COMPLETED_AT": pd.NaT,
        "UPDATED_AT": pd.NaT,
        "STATUS": "OPEN",
    }

    event = namespace["row_to_generic_log"](
        record,
        account_label="prod",
        query_key="security_check_1",
        query_name="users_without_mfa",
        row_index=1,
        generated_at="2026-04-17T12:00:00+00:00",
    )

    assert event["result"]["COMPLETED_AT"] is None
    assert event["result"]["UPDATED_AT"] is None
    assert "source_timestamp" not in event


def test_send_to_secops_dry_run_reports_batches_without_posting():
    namespace = load_helper_namespace()
    events = [
        {"message": "first"},
        {"message": "second"},
        {"message": "third"},
    ]
    config = {
        "SECOPS_WEBHOOK_URL": "https://example.test/import?key=test-key&secret=test-secret",
        "SECOPS_API_KEY": "",
        "SECOPS_WEBHOOK_SECRET": "",
        "BATCH_SIZE": 2,
        "DRY_RUN": True,
    }

    result = namespace["send_to_secops"](
        events,
        config,
        post_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Dry-run mode must not perform HTTP requests.")
        ),
    )

    assert result["planned_batches"] == 2
    assert result["auth_mode"] == "url_query"
    assert result["dry_run"] is True
    assert result["skipped"] is False


def test_describe_auth_mode_handles_url_query_headers_and_mixed():
    namespace = load_helper_namespace()

    assert namespace["describe_auth_mode"]("https://example.test/import") == "headers"
    assert (
        namespace["describe_auth_mode"](
            "https://example.test/import?key=test-key&secret=test-secret"
        )
        == "url_query"
    )
    assert (
        namespace["describe_auth_mode"]("https://example.test/import?key=test-key")
        == "mixed"
    )
