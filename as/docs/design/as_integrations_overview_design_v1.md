# Adaptive Shield Integrations Overview Design (v1)

## Objective
Build a notebook-first workflow that renders an integrations overview UI with strict full-check inventory, failed-check entity details, and local snapshot history.

## Scope
- Use the latest weekly-report notebook as implementation baseline.
- Add a new notebook: `notebooks/as_integrations_overview.ipynb`.
- Fetch all integrations for each account with pagination.
- Fetch full security-check inventory in strict mode:
  - Try account-level endpoint first.
  - Try integration-level endpoint for each integration.
  - Use integration-level results when available for all integrations.
  - Fall back to account-level only when integration-level endpoint is unavailable.
  - Fail the run if no valid inventory endpoint is available.
- Fetch affected entities for failed, non-global checks.
- Persist daily snapshots (Parquet) for history.
- Keep ServiceNow section as empty stub by default.

## Data Flow
1. Build run context with UTC + New York fields.
2. Resolve output directories under:
   - `output/YYYY-MM-DD/Adaptive_Shield/log`
   - `output/YYYY-MM-DD/Adaptive_Shield/overview`
   - `output/YYYY-MM-DD/Adaptive_Shield/history`
3. Fetch accounts.
4. Fetch integrations (paginated).
5. Build strict check inventory.
6. Fetch affected entities for failed checks.
7. Write snapshot parquet datasets.
8. Read snapshot history and build per-check history map.
9. Render UI (account -> integration -> check hierarchy).
10. Export overview artifacts and logs.

## Core Modules
- `src/as_weekly_report/as_client.py`
  - Adds check-list APIs:
    - `get_security_checks_by_account(account_id)`
    - `get_security_checks_by_integration(account_id, integration_id)`
- `src/as_weekly_report/integration_overview.py`
  - Run context and output directory utilities
  - Strict endpoint fallback logic
  - Integration/check/entity normalization
  - Snapshot write/read helpers
  - Daily dedupe and history map builder
  - Overview export helper

## Strict Full-Check Rules
For each account:
- Inventory is valid only if checks can be mapped to integrations.
- Partial integration-level availability is treated as a failure.
- Endpoint-unavailable errors (404/405/501-like) can trigger fallback.
- Failed entities fetch errors are captured in `errors_df` and do not fail the run.

## UI Contract
- Hierarchy: Account -> Integration -> Checks.
- Status grouping in each integration: failed first, passed collapsed by default.
- Failed checks include affected entities details with collapsible payload sections.
- Snapshot history is displayed per check in a collapsible section.

## Export Contract
Under `overview/`:
- `AS_Integrations_Overview_<ts>.xlsx`
- `AS_Integrations_Summary_<ts>.csv`
- `AS_Integrations_Checks_<ts>.csv`
- `AS_Integrations_Entities_<ts>.csv`
- `AS_Integrations_Errors_<ts>.csv`

Under `log/`:
- `run_log_<ts>.json`
- `quality_report_<ts>.csv`

Under `history/`:
- Partitioned snapshot parquet files
- `history_manifest_<ts>.json`

## Configuration
Additional environment variables:
- `OUTPUT_TIMEZONE=America/New_York`
- `SNAPSHOT_GRANULARITY=daily`
- `HISTORY_CACHE_ENABLED=true`
- `HISTORY_UI_LOOKBACK_DAYS=180`
- `INTEGRATION_UI_HISTORY_ENABLED=true`

## Non-Goals
- No ServiceNow live integration in this version.
- No API-based event history reconstruction.
- No automatic retention cleanup.
