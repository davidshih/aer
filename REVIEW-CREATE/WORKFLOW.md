# Workflow and Output Rules

## Output Base Path

All generated output now uses:

- `output/<YYYY-MM-DD>/user-listing/...`

## Stage 2 Highlights

- Enhanced review UI is enabled.
- Email domain typo auto-correction:
  - `@apple-bank.com` -> `@applebank.com`
- For fuzzy top score <= 89:
  - default action is to keep original email/name
  - suggestions remain selectable

## Stage 3 Input Defaults

- If a validated file is uploaded, Stage 3 uses the uploaded file.
- If no upload is provided, Stage 3 automatically uses the latest file from Stage 2 output directory.
- Mapping file default preference:
  - latest `input/mapping/dept*` file
  - fallback to latest CSV under `input/mapping`

## Stage 3 Action Model

- Single button action: `Assign + Save Final Review`
- Assignment and Excel save happen in one run.

## Stage 3 Output Columns

Primary front columns are ordered as:

1. `Validation Status`
2. `is_AD_active`
3. `dept_head`
4. `user_email_validated`
5. `user_fullname_validated`
6. `department_validated`
7. `user_email`
8. `user_fullname`

Additional columns follow after the front columns.

## dept_head Transformation Rules

- Internal assignment writes `dept_head = "yes"` for email exact-match rows.
- Before final save:
  - `dept_head = "yes"` becomes `"confirm assigned reviewer"`
  - `Reviewer` value is wrapped with parentheses for those rows
    - Example: `John Doe` -> `(John Doe)`
- If `dept_head` is empty, it remains empty.

## Data Validation in Excel

- `Reviewer's Response` has dropdown validation:
  - `Approved`, `Denied`, `Changes Required`
- Input prompt is enabled:
  - Title: `Select Action`
  - Message: `Please select: Approved, Denied, or Changes Required`
