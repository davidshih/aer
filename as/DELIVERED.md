# Adaptive Shield Weekly Report - Delivery Summary

## What was delivered

This delivery implements the MVP for Adaptive Shield weekly reporting:

1. Pull alerts in a lookback window (default: 3 days).
2. Filter only `configuration_drift` and `integration_failure`.
3. Enrich alerts with security check details.
4. Expand affected entities for non-global checks.
5. Export report outputs to XLSX and CSV.
6. Keep ServiceNow integration as a stub with ready columns.

## Implemented files

### Project configuration
- `as/.env.example`
- `as/.gitignore`
- `as/requirements.txt`
- `as/PLAN_adaptive_shield_weekly_report_v1.md`

### Python package
- `as/src/as_weekly_report/__init__.py`
- `as/src/as_weekly_report/as_client.py`
- `as/src/as_weekly_report/transform.py`
- `as/src/as_weekly_report/exporter.py`
- `as/src/as_weekly_report/snow_client.py`

### Notebook
- `as/notebooks/as_weekly_report.ipynb` (12 cells)

### Tests
- `as/tests/conftest.py`
- `as/tests/test_as_client.py`
- `as/tests/test_transform.py`
- `as/tests/test_exporter.py`

## Notebook inputs

Environment variables used by the notebook:

- `AS_API_KEY`
- `AS_BASE_URL` (default: `https://api.adaptive-shield.com`)
- `AS_ACCOUNT_IDS` (optional, comma-separated)
- `LOOKBACK_DAYS` (default: `3`)
- `OUTPUT_ROOT` (default: `output`)
- `EXPORT_XLSX` (default: `true`)
- `EXPORT_CSV` (default: `true`)
- `SNOW_ENABLED` (default: `false`)
- `RATE_LIMIT_PER_MINUTE` (default: `90`)
- `REQUEST_TIMEOUT_SECONDS` (default: `30`)
- `MAX_RETRIES` (default: `3`)

## Notebook outputs

Generated under:

- `as/output/YYYY-MM-DD/`

Files:

- `AS_Weekly_Report_{timestamp}.xlsx`
- `AS_Weekly_Summary_{timestamp}.csv`
- `AS_Weekly_Entities_{timestamp}.csv`
- `AS_Weekly_Errors_{timestamp}.csv`

## UI behavior (Configuration Drifts)

The notebook includes a dedicated UI cell for drift review:

1. Auto-group same integration + security check into one merged card.
2. Display grouped checks in a timeline infographic with latest records on top.
3. Detect and mark flip-flops (failed/passed status transitions) with a badge.
4. Group by current status with failed groups first.
5. Keep passed groups folded by default.
6. Include `saas name`, `integration alias`, and `security check name` in the card summary.
7. Keep check details and remediation content folded by default.
8. Keep affected entities folded by default per check card, with expand/collapse support.
9. Show full entity-level details (extra context, usage, raw payload) from `GET .../security_checks/{id}/affected`, each in nested folded sections.
10. Keep event history folded per merged check card.

## Validation completed

1. Python compile check passed.
2. Unit tests passed:
   - `12 passed`

## Quick run

1. Create `.env` from `.env.example` and set `AS_API_KEY`.
2. Install dependencies:
   - `pip install -r as/requirements.txt`
3. Open and run:
   - `as/notebooks/as_weekly_report.ipynb`
