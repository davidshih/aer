from decimal import Decimal
from pathlib import Path

import nbformat
import pandas as pd


NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[1] / "snowflake_trust_center_to_secops.ipynb"
)
HELPER_CELL_PREFIXES = [
    "# Cell 4 - Configuration helpers",
    "# Cell 7 - Selector helpers",
    "# Cell 14 - Query execution helpers",
    "# Cell 17 - Send selection helpers",
    "# Cell 20 - SecOps sender helpers",
]


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
    namespace = {}
    for prefix in HELPER_CELL_PREFIXES:
        exec(find_code_cell_source(notebook, prefix), namespace)
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


def test_notebook_json_is_valid():
    notebook = load_notebook()
    nbformat.validate(notebook)


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


def test_build_default_selection_prefers_first_account_and_all_queries():
    namespace = load_helper_namespace()
    config = make_config(namespace)

    selection = namespace["build_default_selection"](config)

    assert selection == {
        "accounts": ["prod"],
        "queries": ["security_check_1", "security_check_4"],
    }


def test_execute_selected_queries_only_runs_requested_account_query_pairs():
    namespace = load_helper_namespace()
    config = make_config(namespace)
    selection = {"accounts": ["prod", "staging"], "queries": ["security_check_4"]}
    connect_calls = []
    fetch_calls = []

    def fake_connect(account_cfg):
        connect_calls.append(account_cfg["label"])
        return {"label": account_cfg["label"]}

    def fake_fetch(conn, sql):
        fetch_calls.append((conn["label"], sql))
        return pd.DataFrame([{"account": conn["label"], "sql": sql}])

    results = namespace["execute_selected_queries"](
        config,
        selection,
        connect_fn=fake_connect,
        fetch_fn=fake_fetch,
        close_fn=lambda _conn: None,
    )

    assert sorted(results) == [
        "prod::security_check_4",
        "staging::security_check_4",
    ]
    assert connect_calls == ["prod", "staging"]
    assert fetch_calls == [
        ("prod", "SELECT 4"),
        ("staging", "SELECT 4"),
    ]


def test_build_send_candidates_marks_empty_and_failed_groups_unselectable():
    namespace = load_helper_namespace()
    query_results = {
        "prod::security_check_1": {
            "group_key": "prod::security_check_1",
            "account_label": "prod",
            "query_key": "security_check_1",
            "query_name": "users_without_mfa",
            "status": "success",
            "row_count": 2,
            "dataframe": pd.DataFrame([{"value": 1}, {"value": 2}]),
            "error": None,
        },
        "prod::security_check_4": {
            "group_key": "prod::security_check_4",
            "account_label": "prod",
            "query_key": "security_check_4",
            "query_name": "security_check_4",
            "status": "empty",
            "row_count": 0,
            "dataframe": pd.DataFrame(),
            "error": None,
        },
        "staging::security_check_4": {
            "group_key": "staging::security_check_4",
            "account_label": "staging",
            "query_key": "security_check_4",
            "query_name": "security_check_4",
            "status": "error",
            "row_count": 0,
            "dataframe": pd.DataFrame(),
            "error": "permission denied",
        },
    }

    candidates = {
        item["group_key"]: item for item in namespace["build_send_candidates"](query_results)
    }

    assert candidates["prod::security_check_1"]["disabled"] is False
    assert candidates["prod::security_check_1"]["default_selected"] is True
    assert candidates["prod::security_check_4"]["disabled"] is True
    assert candidates["staging::security_check_4"]["disabled"] is True
    assert "permission denied" in candidates["staging::security_check_4"]["reason"]


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
