# Stage 2 Validation Cell Implementation Plan

## Scope

- Update Stage 2 validation UI in `aer_user_listing.json`.
- Reorganize display into G0-G5 groups.
- Add preferred-name override support from `input/preferred_name_changes.csv`.
- Keep Stage 2 save/export behavior unchanged.

## Display Rules

- G0: Auto hidden, summary accordion, folded by default.
- G1: Candidate rows with top score >= 90, listed in accordion, folded by default.
- G2: Candidate rows with top score <= 89, listed directly and expanded.
- G3: Name mismatch rows, listed in accordion, folded by default.
- G4: No-match rows (`ERR_NOT_FOUND` + `ERR_EMAIL_INVALID`), listed read-only in accordion, folded by default.
- G5: Missing-input rows, count only in summary.

## Preferred Name Override

- File path: `input/preferred_name_changes.csv`
- Required columns: `old_name`, `new_name`
- The notebook reloads the CSV on every validation run.
- If `User Name` matches `old_name`, use `new_name` when checking AD by name.
- Email exact-match logic stays unchanged.

## Initial CSV Entries

- `Claudia Palma -> Claudia Bracco`
- `Pamela Berrospi -> Pamela Bilello`
- `Jacqueline Newman -> Jackie Doyle`
- `Rhondalyn Anderson -> Ronda Anderson`

## Validation / Test Plan

- Verify notebook JSON is valid.
- Verify the Stage 2 source still compiles.
- Stub-test preferred-name override lookup.
- Stub-test G1/G2 split, G3 accordion, G4 read-only listing.
- Commit and push only after tests pass.
