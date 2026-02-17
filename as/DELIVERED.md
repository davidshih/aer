# Adaptive Shield Weekly Report - Delivery Summary

## What was delivered

This delivery now includes the original MVP plus ServiceNow incident mapping enhancement:

1. Pull alerts in a lookback window (default: 3 days).
2. Filter only `configuration_drift` and `integration_failure`.
3. Enrich alerts with security check details.
4. Expand affected entities for non-global checks.
5. Export report outputs to XLSX and CSV.
6. Collect ServiceNow incidents via Selenium (`short description` contains `AdaptiveShield`).
7. Map incidents to `SaaS | Alias | Check` and merge ticket status back into summary.
8. Provide an enhanced drift UI with ServiceNow status badges and stale-update hints.

## Implemented files

### Project configuration
- `/Users/davidshih/projects/work/aer/as/.env.example`
- `/Users/davidshih/projects/work/aer/as/.gitignore`
- `/Users/davidshih/projects/work/aer/as/requirements.txt`
- `/Users/davidshih/projects/work/aer/as/PLAN_adaptive_shield_weekly_report_v1.md`

### Python package
- `/Users/davidshih/projects/work/aer/as/src/as_weekly_report/__init__.py`
- `/Users/davidshih/projects/work/aer/as/src/as_weekly_report/as_client.py`
- `/Users/davidshih/projects/work/aer/as/src/as_weekly_report/transform.py`
- `/Users/davidshih/projects/work/aer/as/src/as_weekly_report/exporter.py`
- `/Users/davidshih/projects/work/aer/as/src/as_weekly_report/snow_client.py`

### Notebook
- `/Users/davidshih/projects/work/aer/as/notebooks/as_weekly_report.ipynb` (13 cells)

### Tests
- `/Users/davidshih/projects/work/aer/as/tests/conftest.py`
- `/Users/davidshih/projects/work/aer/as/tests/test_as_client.py`
- `/Users/davidshih/projects/work/aer/as/tests/test_transform.py`
- `/Users/davidshih/projects/work/aer/as/tests/test_exporter.py`

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
- `SNOW_BASE_URL`
- `SNOW_USERNAME`
- `SNOW_PASSWORD`
- `SNOW_COOKIE_PATH`
- `SNOW_HEADLESS` (default: `true`)
- `SNOW_USER_DATA_DIR`
- `SNOW_CHROMEDRIVER_PATH`
- `SNOW_LOGIN_TIMEOUT_SECONDS` (default: `20`)
- `SNOW_MAX_INCIDENTS` (default: `200`)
- `SNOW_FETCH_DETAIL_NOTES` (default: `true`)
- `SNOW_INCIDENT_QUERY` (default: `short_descriptionLIKEAdaptiveShield`)
- `RATE_LIMIT_PER_MINUTE` (default: `90`)
- `REQUEST_TIMEOUT_SECONDS` (default: `30`)
- `MAX_RETRIES` (default: `3`)

## Notebook outputs

Generated under:

- `/Users/davidshih/projects/work/aer/as/output/YYYY-MM-DD/`

Files:

- `AS_Weekly_Report_{timestamp}.xlsx`
- `AS_Weekly_Summary_{timestamp}.csv`
- `AS_Weekly_Entities_{timestamp}.csv`
- `AS_Weekly_Errors_{timestamp}.csv`
- `AS_Weekly_ServiceNow_Tickets_{timestamp}.csv`

## UI behavior

### Cell 8 (baseline Configuration Drifts)
1. Auto-group same integration + security check into one merged card.
2. Display grouped checks in a timeline infographic with latest records on top.
3. Detect and mark flip-flops (failed/passed status transitions) with a badge.
4. Group by current status with failed groups first.
5. Keep passed groups folded by default.
6. Keep details/remediation/entities/history foldable.

### Cell 10 (enhanced with ServiceNow)
1. Re-render drift timeline with ServiceNow context.
2. Add `SN: none / open N / closed N` badge in card header.
3. Add stale hint (`last update Nd ago`) for open incidents.
4. Add folded ServiceNow incidents table:
   - ticket number
   - opened datetime
   - state
   - assigned to
   - last update datetime
   - days ago
   - note source
   - last note (truncated)

## Validation completed

1. Notebook code cells AST parse check passed.
2. Cell sequence updated to 13 cells with new ServiceNow collection and enhanced UI cell.

## Quick run

1. Create `.env` from `.env.example` and set `AS_API_KEY`.
2. If using ServiceNow enhancement, set `SNOW_ENABLED=true` and fill ServiceNow env vars.
3. Install dependencies:
   - `pip install -r /Users/davidshih/projects/work/aer/as/requirements.txt`
4. Open and run:
   - `/Users/davidshih/projects/work/aer/as/notebooks/as_weekly_report.ipynb`
