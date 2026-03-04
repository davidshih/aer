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

## Recent Commits (Past 5 Days)

These branch commits are tracked here so the workspace README reflects the latest notebook and workflow changes.

- 2026-03-03 `d9721ba` Allow blank reviewers in Stage 4 preflight
- 2026-03-03 `6f3682f` Adjust report export status columns
- 2026-03-02 `cd038f2` Sort review output by dept head and AD status
- 2026-03-02 `8f229f7` Reorganize Stage 2 validation groups and add preferred name overrides
- 2026-03-02 `75d872e` Email UI: global app sections and wider preview layout
- 2026-03-02 `1b21de5` Improve Stage 2 review row readability
- 2026-03-02 `ecfe259` Use department to disambiguate AD matches
- 2026-03-02 `c8c5c8e` Use validated user fields in review assignment
- 2026-03-02 `fd93782` Fallback to name match when email is missing from AD
- 2026-03-02 `a44d72d` Refactor REVIEW notebook runtime bootstrap
- 2026-03-02 `f62e5e5` 0302
- 2026-02-27 `4fbbf52` Restore Stage5 default tree load with explicit target lock
- 2026-02-27 `ff4a26a` Require explicit Stage5 folder selection and update Use button state
- 2026-02-27 `54e34fa` Revert Cell 5 split and update SharePoint defaults
- 2026-02-27 `226f785` Split Stage 5 upload and share into separate notebook cells
- 2026-02-27 `7db6b8b` Add Stage5 SPO token fallback in aer_user_listing
- 2026-02-27 `5611270` Force reload .env and use SHAREPOINT_HOST only for SPO token
- 2026-02-27 `2cc0e5f` Enhance Stage5 folder tree with counts and folder metadata
- 2026-02-27 `88f67dc` Use item-id based children lookup for Stage5 folder tree
- 2026-02-27 `ce75b96` Fix Stage5 folder tree Graph children endpoint format
