import os
from pathlib import Path

import nbformat
import pandas as pd


NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[1] / "snowflake_trust_center_to_secops.ipynb"
)
HELPER_CELL_PREFIX = "# Cell 2 - Helpers and configuration"
CONTROL_PANEL_CELL_PREFIX = "# Cell 3 - Unified control panel"
REDESIGNED_CONTROL_PANEL_CELL_PREFIX = "# Cell 5"


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


def write_sql_file(path: Path, metadata: dict, sql: str):
    header = "\n".join(f"-- {key}: {value}" for key, value in metadata.items())
    path.write_text(f"{header}\n\n{sql.strip()}\n", encoding="utf-8")


def make_project_config(namespace, tmp_path: Path):
    sql_dir = tmp_path / "sql_checks"
    sql_dir.mkdir()
    write_sql_file(
        sql_dir / "login_history_activity.sql",
        {
            "title": "Login History Activity",
            "domain": "Authentication",
            "priority": "P0",
            "sources": "ACCOUNT_USAGE.LOGIN_HISTORY",
            "watermark_column": "event_timestamp",
            "timestamp_field": "event_timestamp",
            "native_id_field": "event_id",
            "max_latency_minutes": "120",
            "recommended_cadence": "every_15_minutes",
            "chronicle_log_type": "login_history",
            "description": "Authentication anomaly monitoring.",
        },
        """
        SELECT
            1 AS "event_id",
            CURRENT_TIMESTAMP() AS "event_timestamp",
            'alice' AS "user_name"
        """,
    )
    write_sql_file(
        sql_dir / "query_history_activity.sql",
        {
            "title": "Query History Activity",
            "domain": "Query and Control Plane",
            "priority": "P0",
            "sources": "ACCOUNT_USAGE.QUERY_HISTORY",
            "watermark_column": "start_time",
            "timestamp_field": "event_timestamp",
            "native_id_field": "query_id",
            "max_latency_minutes": "45",
            "recommended_cadence": "every_15_minutes",
            "chronicle_log_type": "query_history",
            "description": "Control plane and risky query monitoring.",
        },
        """
        SELECT
            'q-1' AS "query_id",
            CURRENT_TIMESTAMP() AS "event_timestamp",
            CURRENT_TIMESTAMP() AS "start_time",
            'GRANT' AS "query_type",
            'GRANT ROLE ACCOUNTADMIN TO USER ALICE' AS "query_text"
        """,
    )

    env = {
        "SNOWFLAKE_ACCOUNT_1": "prod-account.us-east-1",
        "SNOWFLAKE_USER_1": "svc_prod",
        "SNOWFLAKE_PRIVATE_KEY_PATH_1": "~/.snowflake/prod.p8",
        "SNOWFLAKE_LABEL_1": "prod",
        "SNOWFLAKE_ACCOUNT_2": "staging-account.us-east-1",
        "SNOWFLAKE_USER_2": "svc_staging",
        "SNOWFLAKE_PRIVATE_KEY_PATH_2": "~/.snowflake/staging.p8",
        "SNOWFLAKE_LABEL_2": "staging",
        "SECURITY_CHECK_NAME_1": "login_history_activity",
        "SECURITY_CHECK_SQL_FILE_1": "sql_checks/login_history_activity.sql",
        "SECURITY_CHECK_NAME_2": "query_history_activity",
        "SECURITY_CHECK_SQL_FILE_2": "sql_checks/query_history_activity.sql",
        "SECURITY_CHECK_NAME_3": "inline_custom_check",
        "SECURITY_CHECK_SQL_3": "SELECT CURRENT_ACCOUNT() AS account_name",
        "SECOPS_WEBHOOK_URL": "https://example.test/import?key=test-key&secret=test-secret",
        "BATCH_SIZE": "25",
        "DRY_RUN": "true",
    }
    config = namespace["build_runtime_config"](
        env,
        project_dir=tmp_path,
        env_path=tmp_path / ".env",
        prompt_for_missing=False,
    )
    return config, env


def make_success_result(namespace, config, group_key: str, rows: list[dict], status="success"):
    group_meta = namespace["build_group_catalog"](config)["group_lookup"][group_key]
    result = namespace["build_empty_query_result"](group_meta)
    result["dataframe"] = pd.DataFrame(rows)
    result["columns"] = result["dataframe"].columns.tolist()
    result["row_count"] = len(result["dataframe"])
    result["status"] = status if rows else "empty"
    return result


def load_redesigned_control_panel_namespace(tmp_path: Path):
    namespace = load_helper_namespace()
    notebook = load_notebook()
    config, _env = make_project_config(namespace, tmp_path)
    namespace["CONFIG"] = config
    namespace["APP_STATE"] = namespace["create_app_state"](config)
    exec(find_code_cell_source(notebook, REDESIGNED_CONTROL_PANEL_CELL_PREFIX), namespace)
    return namespace, config


def seed_redesigned_control_panel_ready_state(namespace, config):
    app_state = namespace["APP_STATE"]
    selected_group = app_state["checked_groups"][0]
    app_state["query_results"][selected_group] = make_success_result(
        namespace,
        config,
        selected_group,
        [{"event_id": 1, "event_timestamp": "2026-04-17T15:00:00Z"}],
    )
    app_state["last_run_selection"] = namespace["get_selection_snapshot"](
        app_state["checked_groups"],
        app_state["dry_run"],
        app_state["group_catalog"],
    )
    app_state["selection_dirty"] = False
    app_state["dirty_reason"] = "Ready to send."
    namespace["_render"]()
    return selected_group


def test_notebook_json_is_valid():
    notebook = load_notebook()
    nbformat.validate(notebook)


def test_notebook_has_legacy_and_redesigned_control_panel_ui():
    notebook = load_notebook()

    assert len(notebook.cells) >= 5

    legacy_panel_source = find_code_cell_source(notebook, CONTROL_PANEL_CELL_PREFIX)
    assert "DOMAIN_CARDS_BOX" in legacy_panel_source
    assert "RUN_TABLE_BOX" in legacy_panel_source
    assert "SelectMultiple" in legacy_panel_source
    assert 'description="DRY_RUN"' in legacy_panel_source
    assert 'description="Run Selected"' in legacy_panel_source
    assert 'description="Send Selected to SecOps"' in legacy_panel_source
    assert "Check Catalog" in legacy_panel_source
    assert "Run Table" in legacy_panel_source

    redesigned_panel_source = find_code_cell_source(
        notebook, REDESIGNED_CONTROL_PANEL_CELL_PREFIX
    )
    assert "acct_boxes" in redesigned_panel_source
    assert "check_boxes" in redesigned_panel_source
    assert 'description="DRY RUN"' in redesigned_panel_source
    assert 'description="Run Selected"' in redesigned_panel_source
    assert 'description="Send to SecOps"' in redesigned_panel_source
    assert "output_tabs = widgets.Tab" in redesigned_panel_source
    assert 'output_tabs.set_title(0, "Run Log")' in redesigned_panel_source
    assert 'output_tabs.set_title(1, "Preview")' in redesigned_panel_source
    assert 'output_tabs.set_title(2, "SecOps Log")' in redesigned_panel_source


def test_build_runtime_config_loads_sql_file_metadata_and_inline_fallback(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)

    assert [account["label"] for account in config["SNOWFLAKE_ACCOUNTS"]] == [
        "prod",
        "staging",
    ]
    assert [check["key"] for check in config["SECURITY_CHECKS"]] == [
        "login_history_activity",
        "query_history_activity",
        "inline_custom_check",
    ]
    assert config["SECURITY_CHECKS"][0]["title"] == "Login History Activity"
    assert config["SECURITY_CHECKS"][0]["domain"] == "Authentication"
    assert config["SECURITY_CHECKS"][0]["chronicle_log_type"] == "login_history"
    assert config["SECURITY_CHECKS"][0]["sql_path"].endswith(
        "sql_checks/login_history_activity.sql"
    )
    assert config["SECURITY_CHECKS"][2]["chronicle_log_type"] == "custom_query"
    assert config["SECURITY_CHECKS"][2]["sql"] == "SELECT CURRENT_ACCOUNT() AS account_name"


def test_redesigned_control_panel_clears_dirty_state_when_selection_is_restored(tmp_path):
    namespace, config = load_redesigned_control_panel_namespace(tmp_path)
    seed_redesigned_control_panel_ready_state(namespace, config)

    namespace["check_boxes"]["query_history_activity"].value = False

    assert namespace["APP_STATE"]["selection_dirty"] is True
    assert "rerun required" in namespace["APP_STATE"]["dirty_reason"]
    assert namespace["send_btn"].disabled is True

    namespace["check_boxes"]["query_history_activity"].value = True

    assert namespace["APP_STATE"]["selection_dirty"] is False
    assert namespace["APP_STATE"]["dirty_reason"] == "Ready to send."
    assert namespace["send_btn"].disabled is False


def test_redesigned_control_panel_marks_mode_changes_dirty_until_restored(tmp_path):
    namespace, config = load_redesigned_control_panel_namespace(tmp_path)
    seed_redesigned_control_panel_ready_state(namespace, config)

    original_dry_run = namespace["dry_run_btn"].value
    namespace["dry_run_btn"].value = not original_dry_run

    assert namespace["APP_STATE"]["selection_dirty"] is True
    assert namespace["APP_STATE"]["dirty_reason"] == "Mode changed; rerun required before send."
    assert namespace["send_btn"].disabled is True

    namespace["dry_run_btn"].value = original_dry_run

    assert namespace["APP_STATE"]["selection_dirty"] is False
    assert namespace["APP_STATE"]["dirty_reason"] == "Ready to send."
    assert namespace["send_btn"].disabled is False


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


def test_create_app_state_defaults_to_first_account_visible_rows_only(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)

    app_state = namespace["create_app_state"](config)

    assert app_state["selected_accounts"] == ["prod"]
    assert app_state["selected_checks"] == [
        "login_history_activity",
        "query_history_activity",
        "inline_custom_check",
    ]
    assert app_state["checked_groups"] == [
        "prod::login_history_activity",
        "prod::query_history_activity",
        "prod::inline_custom_check",
    ]


def test_set_check_selection_state_updates_visible_checked_groups(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    app_state = namespace["create_app_state"](config)

    namespace["set_check_selection_state"](app_state, "query_history_activity", False)

    assert "prod::query_history_activity" not in app_state["checked_groups"]
    assert app_state["group_selection_state"]["staging::query_history_activity"] is False


def test_build_run_table_rows_exposes_domain_and_log_type_metadata(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    app_state = namespace["create_app_state"](config)

    rows = namespace["build_run_table_rows"](config, app_state)

    assert len(rows) == 3
    assert rows[0]["account"] == "prod"
    assert rows[0]["domain"] == "Authentication"
    assert rows[0]["log_type"] == "login_history"
    assert rows[1]["source"] == "ACCOUNT_USAGE.QUERY_HISTORY"


def test_execute_selected_groups_only_runs_requested_rows(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    selected_group_keys = [
        namespace["make_group_key"]("prod", "query_history_activity"),
        namespace["make_group_key"]("staging", "query_history_activity"),
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
    assert all("GRANT ROLE ACCOUNTADMIN" in sql for _label, sql in fetch_calls)


def test_sync_runtime_selection_marks_dry_run_change_dirty_after_run(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    app_state = namespace["create_app_state"](config)
    app_state["last_run_selection"] = namespace["get_selection_snapshot"](
        app_state["checked_groups"],
        app_state["dry_run"],
        app_state["group_catalog"],
    )

    namespace["sync_runtime_selection"](app_state, app_state["checked_groups"], False)

    assert app_state["selection_dirty"] is True
    assert "Mode changed" in app_state["dirty_reason"]


def test_build_parser_friendly_event_truncates_query_text_and_adds_hash(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    group_key = "prod::query_history_activity"
    query_result = make_success_result(
        namespace,
        config,
        group_key,
        [
            {
                "query_id": "q-1",
                "event_timestamp": pd.Timestamp("2026-04-17T15:00:00Z"),
                "query_text": "X" * 10120,
                "query_type": "GRANT",
            }
        ],
    )

    event = namespace["build_parser_friendly_event"](
        query_result["dataframe"].to_dict(orient="records")[0],
        query_result=query_result,
        generated_at="2026-04-17T16:00:00+00:00",
        row_index=1,
        query_text_limit=10000,
    )

    assert event["application"] == "snowflake"
    assert event["environment"] == "prod"
    assert event["log_type"] == "query_history"
    assert event["event_timestamp"] == "2026-04-17T15:00:00+00:00"
    assert len(event["query_text"]) < 10120
    assert event["query_text_truncated"] is True
    assert len(event["query_text_sha256"]) == 64
    assert event["record_uid"].startswith("query_history:prod:q-1")


def test_build_parser_friendly_event_handles_nat_and_nested_values(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    group_key = "prod::login_history_activity"
    query_result = make_success_result(
        namespace,
        config,
        group_key,
        [
            {
                "event_id": 99,
                "event_timestamp": pd.NaT,
                "login_details": {"risk": "medium"},
                "user_name": "alice",
            }
        ],
    )

    event = namespace["build_parser_friendly_event"](
        query_result["dataframe"].to_dict(orient="records")[0],
        query_result=query_result,
        generated_at="2026-04-17T16:00:00+00:00",
        row_index=1,
    )

    assert event["event_timestamp"] is None or "event_timestamp" not in event
    assert event["login_details"] == {"risk": "medium"}
    assert event["event_id"] == 99


def test_build_selected_events_uses_parser_friendly_log_types(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    app_state = namespace["create_app_state"](config)
    login_group = "prod::login_history_activity"
    query_group = "prod::query_history_activity"

    app_state["query_results"][login_group] = make_success_result(
        namespace,
        config,
        login_group,
        [{"event_id": 1, "event_timestamp": "2026-04-17T15:00:00Z", "user_name": "alice"}],
    )
    app_state["query_results"][query_group] = make_success_result(
        namespace,
        config,
        query_group,
        [{"query_id": "q-1", "event_timestamp": "2026-04-17T15:10:00Z", "query_type": "GRANT"}],
    )

    events, payload_plan = namespace["build_selected_events"](
        app_state["query_results"],
        [login_group, query_group],
        dry_run=True,
    )

    assert len(events) == 2
    assert {event["log_type"] for event in events} == {"login_history", "query_history"}
    assert payload_plan["dry_run"] is True
    assert payload_plan["selected_groups"][0]["log_type"] == "login_history"


def test_reduce_send_state_requires_clean_successful_rows(tmp_path):
    namespace = load_helper_namespace()
    config, _env = make_project_config(namespace, tmp_path)
    app_state = namespace["create_app_state"](config)
    selected_group = app_state["checked_groups"][0]

    app_state["query_results"][selected_group] = make_success_result(
        namespace,
        config,
        selected_group,
        [{"event_id": 1, "event_timestamp": "2026-04-17T15:00:00Z"}],
    )
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
