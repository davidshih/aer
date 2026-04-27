from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import snowflake_secops_daily_runner as runner


class FakeResponse:
    status_code = 200
    text = "OK"
    headers = {}


def write_sql_file(path: Path, metadata: dict, sql: str) -> None:
    header = "\n".join(f"-- {key}: {value}" for key, value in metadata.items())
    path.write_text(f"{header}\n\n{sql.strip()}\n", encoding="utf-8")


def make_project_config(tmp_path: Path, dry_run: str = "true"):
    helpers = runner.load_notebook_helpers()
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
            "chronicle_log_type": "login_history",
        },
        """
        SELECT
            1 AS "event_id",
            CURRENT_TIMESTAMP() AS "event_timestamp"
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
            "chronicle_log_type": "query_history",
        },
        """
        SELECT
            'q-1' AS "query_id",
            CURRENT_TIMESTAMP() AS "event_timestamp",
            'GRANT' AS "query_type"
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
        "SECOPS_WEBHOOK_URL": "https://example.test/import?key=test-key&secret=test-secret",
        "BATCH_SIZE": "25",
        "DRY_RUN": dry_run,
    }
    config = helpers["build_runtime_config"](
        env,
        project_dir=tmp_path,
        env_path=tmp_path / ".env",
        prompt_for_missing=False,
    )
    return helpers, config, env


def no_sanity(config, account_labels, connect_fn=None, close_fn=None):
    return [
        {
            "account_label": account_label,
            "status": "skipped",
        }
        for account_label in account_labels
    ]


def fake_connect(account_config):
    return {"label": account_config["label"]}


def close_noop(_conn):
    return None


def one_event_frame(_conn, _sql):
    return pd.DataFrame(
        [
            {
                "event_id": 1,
                "event_timestamp": pd.Timestamp("2026-04-17T15:00:00Z"),
            }
        ]
    )


def test_resolve_selected_groups_from_csv(tmp_path):
    helpers, config, env = make_project_config(tmp_path)
    env["SELECTED_ACCOUNTS"] = "prod, staging"
    env["SELECTED_CHECKS"] = "login_history_activity"

    selection = runner.resolve_selected_groups(config, env, helpers)

    assert selection["accounts"] == ["prod", "staging"]
    assert selection["checks"] == ["login_history_activity"]
    assert selection["groups"] == [
        "prod::login_history_activity",
        "staging::login_history_activity",
    ]


def test_resolve_selected_groups_expands_all(tmp_path):
    helpers, config, env = make_project_config(tmp_path)
    env["SELECTED_ACCOUNTS"] = "all"
    env["SELECTED_CHECKS"] = "all"

    selection = runner.resolve_selected_groups(config, env, helpers)

    assert selection["accounts"] == ["prod", "staging"]
    assert selection["checks"] == ["login_history_activity", "query_history_activity"]
    assert selection["groups"] == [
        "prod::login_history_activity",
        "prod::query_history_activity",
        "staging::login_history_activity",
        "staging::query_history_activity",
    ]


def test_resolve_selected_groups_rejects_unknown_values(tmp_path):
    helpers, config, env = make_project_config(tmp_path)
    env["SELECTED_ACCOUNTS"] = "prod,missing"
    env["SELECTED_CHECKS"] = "login_history_activity"

    with pytest.raises(runner.DailyRunnerError, match="Unknown SELECTED_ACCOUNTS"):
        runner.resolve_selected_groups(config, env, helpers)


def test_resolve_selected_groups_requires_explicit_selection(tmp_path):
    helpers, config, env = make_project_config(tmp_path)

    with pytest.raises(runner.DailyRunnerError, match="SELECTED_ACCOUNTS is required"):
        runner.resolve_selected_groups(config, env, helpers)


def test_execute_daily_run_dry_run_does_not_post(tmp_path):
    helpers, config, env = make_project_config(tmp_path, dry_run="true")
    env["SELECTED_ACCOUNTS"] = "prod"
    env["SELECTED_CHECKS"] = "login_history_activity"

    summary = runner.execute_daily_run(
        config,
        env,
        helpers,
        connect_fn=fake_connect,
        fetch_fn=one_event_frame,
        close_fn=close_noop,
        sanity_fn=no_sanity,
        post_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Dry-run mode must not post.")
        ),
    )

    assert summary["status"] == "success"
    assert summary["dry_run"] is True
    assert summary["payload_plan"]["total_events"] == 1
    assert summary["secops_result"]["dry_run"] is True
    assert summary["secops_result"]["planned_batches"] == 1
    assert summary["secops_result"]["sent"] == 0


def test_execute_daily_run_blocks_send_when_query_errors(tmp_path):
    helpers, config, env = make_project_config(tmp_path, dry_run="false")
    env["SELECTED_ACCOUNTS"] = "prod"
    env["SELECTED_CHECKS"] = "login_history_activity"

    def failing_fetch(_conn, _sql):
        raise RuntimeError("query failed")

    with pytest.raises(runner.DailyRunnerError) as exc_info:
        runner.execute_daily_run(
            config,
            env,
            helpers,
            connect_fn=fake_connect,
            fetch_fn=failing_fetch,
            close_fn=close_noop,
            sanity_fn=no_sanity,
            post_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("Query errors must block posting.")
            ),
        )

    assert "Selected query errors blocked SecOps delivery" in str(exc_info.value)
    assert exc_info.value.summary["status"] == "error"
    assert exc_info.value.summary["query_errors"][0]["error"] == "query failed"


def test_execute_daily_run_success_posts_live_events(tmp_path):
    helpers, config, env = make_project_config(tmp_path, dry_run="false")
    env["SELECTED_ACCOUNTS"] = "prod"
    env["SELECTED_CHECKS"] = "login_history_activity"
    post_calls = []

    def fake_post(url, headers, data, timeout):
        post_calls.append(
            {
                "url": url,
                "headers": headers,
                "data": data,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    summary = runner.execute_daily_run(
        config,
        env,
        helpers,
        connect_fn=fake_connect,
        fetch_fn=one_event_frame,
        close_fn=close_noop,
        sanity_fn=no_sanity,
        post_fn=fake_post,
    )

    assert summary["status"] == "success"
    assert summary["dry_run"] is False
    assert summary["payload_plan"]["total_events"] == 1
    assert summary["secops_result"]["sent"] == 1
    assert len(post_calls) == 1
    assert post_calls[0]["url"] == env["SECOPS_WEBHOOK_URL"]
