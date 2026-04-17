# Snowflake Trust Center to Google SecOps Notebook

This directory contains the standalone Snowflake security-check notebook and the SQL checks it runs before building Google SecOps payloads.

## Files

- `snowflake_trust_center_to_secops.ipynb`: Main standalone notebook for running Snowflake checks and sending selected results to Google SecOps.
- `snowflake_connection_diagnostics.ipynb`: Connectivity and credential diagnostics for Snowflake accounts.
- `sql_checks/`: SQL checks with metadata headers consumed by the notebook runtime.
- `tests/test_snowflake_secops_notebook.py`: Regression tests for notebook helpers and control-panel behavior.
- `.env.example`: Environment template for Snowflake accounts, checks, and SecOps credentials.

## Notebook Flow

Run the notebook cells in order:

1. Cell 1 installs notebook dependencies.
2. Cell 2 loads `.env`, builds the runtime config, and initializes `APP_STATE`.
3. Cell 3 provides the original domain-card and run-table control panel.
4. Cell 4 prints a debug snapshot of the current runtime state.
5. Cell 5 provides the redesigned control panel.

Cell 5 is the recommended operator UI when you want a compact account-by-check matrix and tabbed output panes.

## Redesigned Control Panel (Cell 5)

The redesigned panel keeps the same execution helpers as the legacy UI, but presents them as four compact zones:

- Account toggles
- Check toggles
- Live account-by-check status matrix
- Action bar with `DRY RUN`, `Run Selected`, and `Send to SecOps`

The bottom output area is split into three tabs:

- `Run Log`: Shows run startup details, sanity checks, and the execution summary.
- `Preview`: Shows the latest payload plan, first event preview, and successful query result samples.
- `SecOps Log`: Shows send attempts and the final response or error payload.

## Runtime State Rules

Cell 5 now uses the shared selection-sync helpers from Cell 2, so the UI follows the same rerun rules as the legacy panel:

- Changing the selected accounts or checks marks the run dirty only when it no longer matches the last completed run.
- Restoring the exact previous selection clears the dirty state and re-enables send when eligible results already exist.
- Toggling `DRY RUN` after a completed run marks the selection dirty until the mode is restored or the rows are rerun.
- `Send to SecOps` stays disabled until there is at least one successful non-empty selected result and the current selection matches the latest completed run.

## Configuration

Copy `.env.example` to `.env` and set:

- One or more `SNOWFLAKE_ACCOUNT_<N>` blocks
- `SECURITY_CHECK_NAME_<N>` plus either `SECURITY_CHECK_SQL_FILE_<N>` or `SECURITY_CHECK_SQL_<N>`
- `SECOPS_WEBHOOK_URL`
- `SECOPS_API_KEY` and `SECOPS_WEBHOOK_SECRET` when the webhook URL does not already include `key=` and `secret=`

Relative SQL file paths are resolved from this directory.

## Testing

Run the notebook regression tests with:

```bash
pytest -q tests/test_snowflake_secops_notebook.py
```

These tests validate notebook JSON integrity, helper behavior, legacy UI coverage, and redesigned Cell 5 state-sync behavior.
