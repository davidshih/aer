# AER User Listing Workspace

This workspace is cleaned and centered around one active notebook JSON:

- `aer_user_listing.json`

All previous files are archived under:

- `archive/cleanup_20260225_175745/`

## Current Structure

- `aer_user_listing.json`: latest working notebook JSON for user-listing flow.
- `archive/`: historical files and previous snapshots.
- `WORKFLOW.md`: detailed behavior and output rules.

## Quick Usage

1. Open `aer_user_listing.json` in Jupyter-compatible workflow.
2. Run Stage 1 -> Stage 2 -> Stage 3.
3. Stage 3 defaults to the latest Stage 2 output when no upload is provided.
4. Stage 3 runs assign + save in one action.
