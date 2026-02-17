# Adaptive Shield Snapshot Partition Design (v1)

## Goals
- Persist local history without API event backfill.
- Keep current implementation at daily granularity.
- Reserve schema and partition layout for hourly cron in future.
- Keep model fields in both UTC and New York time.

## Time Model
Every snapshot row carries:
- `run_ts_utc`
- `run_ts_ny`
- `snapshot_date_utc`
- `snapshot_date_ny`
- `snapshot_hour_utc`
- `snapshot_hour_ny`
- `snapshot_granularity`

`output/YYYY-MM-DD` uses New York date.
Partition keys use UTC for DST-safe daily/hourly evolution.

## Directory Layout
Root (per run day in NY):
- `output/<snapshot_date_ny>/Adaptive_Shield/`
  - `log/`
  - `overview/`
  - `history/`

History datasets:
- `history/check_snapshot/granularity=daily/snapshot_date_utc=YYYY-MM-DD/*.parquet`
- `history/failed_entities_snapshot/granularity=daily/snapshot_date_utc=YYYY-MM-DD/*.parquet`

Future hourly layout:
- `history/<dataset>/granularity=hourly/snapshot_date_utc=YYYY-MM-DD/snapshot_hour_utc=HH/*.parquet`

## Write Semantics
- Append-only files per run timestamp.
- Filename convention: `<dataset>_<run_ts_utc_token>.parquet`.
- Manifest file per run:
  - `history/history_manifest_<run_ts_utc_token>.json`

## Read Semantics
- Read all parquet files for a dataset from partition tree.
- Optional lookback filter by `snapshot_date_utc`.
- For daily view, dedupe by:
  - key: `(account_id, integration_id, security_check_id, snapshot_date_ny)`
  - keeper: latest `run_ts_utc`

## Rationale
- UTC partitions avoid DST edge cases for hourly rollout.
- New York fields satisfy business-day and operational reporting requirements.
- Append-only snapshots preserve auditability and rerun traceability.

## Retention
- Current default: keep all history files.
- Cleanup policy intentionally deferred.
