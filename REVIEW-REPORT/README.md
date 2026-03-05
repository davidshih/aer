# AER Review Report Workspace

This folder contains the working notebook used to generate the entitlement review report and send reviewer reminder emails.

## Files

- `aer_report_0224.ipynb`: main notebook (Cells 1 / 2 / 5 / 6).
- `aer_report_v4.2.json`: snapshot/export used by previous iterations.

## Quick Usage

1. Run **Cell 1** to authenticate and initialize logging.
2. Run **Cell 2** to expand categories and select apps.
   - Each expanded category shows a progress bar while loading the app list.
3. Run **Cell 5** to scan selected apps.
   - A per-app progress table shows overall scan progress; detailed per-reviewer steps are written to the log file.
4. Run **Cell 6** to review the generated emails and send messages.

## Logs

Cell 1 prints the log file location. By default it writes to:

- `output/<YYYY-MM-DD>/report/logs/aer_<YYYY-MM-DD>_<HH>00.log`

## Cell 6: Email Notification Center

### App Sections (Global)

- Set each app to **New / Follow-up / Skip** once at the top.
- The selection applies to **all reviewer emails**.

### Global + Per-app Send/Due Dates

- **Global Send / Global Due** apply to **auto** apps only (manual overrides are not overwritten).
- Per-app **Send / Due** can be edited at the app row level.
- Default rule: **Due = Send + 14 days**.
  - Once **Due** is manually edited for an app, it stops auto-updating when **Send** changes.

### Shared Mailbox / Sender

- Use **Send From** to specify the mailbox UPN/email to send from.
- The notebook sends via Graph:
  - `POST /v1.0/users/{sender_mailbox}/sendMail`
- The signed-in account must have permission to send as/on-behalf of the shared mailbox, and the token must include `Mail.Send`.

### Email Body UI

- Email preview auto-expands (no fixed internal scroll area).
- Table headers use **Quarter** and **Users to review**.
- Link column is rendered as a button ("Open Folder") for easier clicking.

