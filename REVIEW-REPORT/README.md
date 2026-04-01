# AER Review Report Workspace

## Overview

This workspace contains a standalone Jupyter notebook, `aer_report_0401.ipynb`, used to:

- authenticate to Microsoft Graph,
- browse the SharePoint review folder structure,
- scan reviewer workbooks for response status,
- build dashboard-style progress summaries,
- export report files for follow-up,
- prepare and send reminder emails to reviewers.

The notebook is designed as a single operational tool for the reporting side of the AER process. It does not build the original user listing files. Instead, it reads the reviewer workbooks that already exist in SharePoint and turns them into a progress view plus outbound reminders.

## Main Notebook

- `aer_report_0401.ipynb`: current working notebook
- `email_defaults.json`: optional defaults for email subject/body/reply-to/cc
- `output/<YYYY-MM-DD>/...`: generated logs, cache files, and exported reports

## Notebook Structure

The notebook has five cells.

### Cell 0: Title / Description

This is the markdown header. It documents the notebook purpose and current version date.

### Cell 1: Setup & Authentication

Responsibilities:

- load environment variables,
- initialize logging,
- authenticate with Microsoft Graph,
- expose shared HTTP helpers with retry and silent token refresh support.

Important globals created here:

- `headers`
- `logger`
- `graph_get()`
- `graph_post()`
- `site_id` is not created here, but later cells depend on the auth state established here.

### Cell 2: SharePoint API & App Selector

Responsibilities:

- resolve the SharePoint site ID,
- list category folders and app folders,
- let the operator select target apps,
- optionally enable cache usage for the scan step.

Key behavior:

- follows `@odata.nextLink` so multi-page Graph results are fully collected,
- filters non-business folders such as `Forms`, `_private`, `audit`, and similar utility folders,
- shows app-level folder counts during selection.

Important globals created here:

- `site_id`
- `TARGET_APPS`
- `USE_CACHE`
- `list_folders_with_count()`
- `list_excel_files()`
- `download_file()`
- `get_file_audit_info()`

### Cell 5: Scan Engine, Dashboard, and Report Export

Responsibilities:

- scan each selected app,
- inspect reviewer workbooks,
- detect completed vs pending reviewer responses,
- maintain a local JSON cache,
- build progress tables and app/reviewer summaries,
- export app-level and global report files.

Design notes:

- scan work is parallelized per reviewer folder with a fixed worker count,
- cache is reused only when the file version is unchanged and the cached rows are already complete,
- pending cache entries are re-read live,
- cache writes use an atomic temp-file replace pattern,
- audit/version history is only fetched after workbook parsing finds real reviewer rows,
- folder URL lookup is keyed by `Category + App_Name + reviewer` so duplicate app names across categories stay correct.

Primary data objects produced here:

- `df`: row-level scan output
- `stats`: grouped app-reviewer summary
- `unified_data`: dashboard structure grouped by app

Outputs written here:

- `aer_cache.json`
- `aer_manual_notes.json` (read when present)
- `output/<date>/report/*.xlsx`
- `output/<date>/report/logs/*.log`

### Cell 7: Email Notification Center

Responsibilities:

- derive pending reviewer targets from scan results,
- resolve reviewer email addresses from AD cache,
- build previewable reminder emails,
- optionally send messages through Microsoft Graph.

This cell expects scan results from Cell 5. It is intentionally tolerant of slightly different global variable layouts and will reuse:

- `df`
- `stats`
- `headers` or `token_mgr`

## Normal Run Order

1. Run Cell 1.
2. Run Cell 2.
3. Select the apps you want to scan.
4. Run Cell 5.
5. Review dashboard output and export reports if needed.
6. Run Cell 7 only when reminder emails are needed.

## Inputs, Cache, and Outputs

### Required environment variables

Expected values include:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `SHAREPOINT_HOST`
- `SITE_NAME`
- `SENDER_EMAIL`

### Local files used by the notebook

- `aer_cache.json`: row cache for workbook scan results
- `aer_manual_notes.json`: optional manual app metadata
- `email_defaults.json`: optional defaults for email composition
- `input/ad_cache/ad_users_*.csv` or `output/<date>/ad_cache/ad_users_*.csv`: AD cache for reviewer email resolution

### Generated files

- `output/<date>/report/logs/aer_<date>_<hour>00.log`
- `output/<date>/report/<app>_<date>.xlsx`
- `output/<date>/report/Summary_Report_<date>.xlsx`
- `output/<date>/checkpoints/email_sent.json`

## Operational Constraints

- Run the notebook from the `REVIEW-REPORT` directory so relative paths stay correct.
- Cell 1 opens an interactive login flow in the browser.
- Cell 7 can send real email. Treat it as a production action.
- This notebook assumes the SharePoint review structure already exists.

## Change Philosophy

The current notebook favors low-risk operational stability over architectural abstraction:

- keep the tool standalone,
- keep data contracts stable between cells,
- avoid changing cache schema unless necessary,
- optimize Graph I/O and scan correctness before attempting larger refactors.
