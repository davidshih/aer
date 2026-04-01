# AER Review Report Workspace for a 5th Grader

## What is this?

This folder has a notebook called `aer_report_0401.ipynb`.

Think of the notebook like a very careful robot helper.

It does not decide who should have access. It also does not create the original review sheets.

Its job is to:

1. sign in,
2. open the right SharePoint folders,
3. read the review Excel files,
4. figure out which reviews are done and which are still missing,
5. show a progress board,
6. save report files,
7. help send reminder emails.

So the notebook is mostly a **checker + reporter + reminder sender**.

## What are the pieces?

The notebook has five cells. A cell is just one chunk of notebook code.

### Cell 0: The label

This is the title at the top.

It tells you what the notebook is for.

### Cell 1: The front door

This cell:

- reads settings,
- starts logging,
- signs in to Microsoft,
- gets permission to talk to Graph and SharePoint.

You can think of this cell like getting a badge before entering a building.

Without this badge, the later cells cannot do their jobs.

It also creates helper functions that know how to:

- call Microsoft Graph,
- wait and retry if Graph says “too many requests,”
- refresh the sign-in token if it gets old.

That matters because the notebook may need to read many files, and cloud systems are sometimes slow or picky.

### Cell 2: The map reader

This cell walks through the SharePoint folder tree.

It finds:

- quarter folders,
- app folders,
- reviewer folders,
- workbook files.

It also shows checkboxes so the operator can choose which apps to scan.

This is like opening a giant filing cabinet and picking which drawers you want to inspect.

The notebook now knows how to keep reading if SharePoint gives the folder list in multiple pages.

That is important because some systems only hand you part of the list at first and say, “click next for more.”

### Cell 5: The main worker

This is the biggest and most important cell.

It does the real scanning work.

For each selected app, it:

1. looks inside the reviewer folders,
2. finds the Excel workbook,
3. reads the sheet,
4. finds the columns it cares about,
5. checks each row for reviewer responses,
6. counts things like approved, denied, changed, and missing,
7. builds summary tables,
8. saves export files.

This cell also uses a cache.

A cache is like a notebook of earlier answers.

If a file did not change and the old scan result is still good, the notebook can reuse that answer instead of reading the whole file again.

That saves time.

But it is careful:

- if the workbook changed, it scans again;
- if the cached result still had missing responses, it scans again;
- if the cached result was already complete and the file did not change, it can trust the cache.

The notebook also tries to be safe when saving cache files.

Instead of writing directly into the main cache file right away, it writes to a temporary file first and then swaps it into place.

That helps prevent broken files if something crashes in the middle.

Another careful thing:

it only asks SharePoint for full file version history after it has already found real reviewer rows in the workbook.

Why?

Because version history is extra work.

If there is nothing useful in the workbook for that reviewer, asking for history is a waste of time.

### Cell 7: The reminder helper

This cell uses the scan result from Cell 5.

It looks for reviewers who still have missing responses.

Then it:

- finds their email addresses,
- prepares reminder emails,
- shows previews,
- can send the messages through Microsoft Graph.

This means Cell 7 is the “please finish your homework” part of the notebook.

It does not guess who should get a reminder by itself.

It depends on Cell 5 to tell it which reviews are still unfinished.

## What files does it read?

The notebook uses several kinds of files:

### Excel review files in SharePoint

These are the main files being scanned.

They contain the reviewer responses.

### `aer_cache.json`

This is the saved memory of old scan results.

### `aer_manual_notes.json`

This can store extra manual notes or status choices.

### `email_defaults.json`

This can store default email text, subject, CC, and reply-to values.

### AD cache CSV files

These help the notebook map reviewer names to email addresses.

Without those files, Cell 7 may not know where to send reminders.

## What files does it create?

It creates:

- log files,
- report Excel files,
- cache files,
- email checkpoint files.

These usually go under `output/<date>/...`

That means each day gets its own output folder, which helps keep runs organized.

## Why are there dashboards?

People usually do not want to read every single row in every workbook just to answer:

- Which apps are done?
- Which reviewers are late?
- How much work is left?

So the notebook turns row-by-row workbook data into simple progress summaries.

That is what the dashboard is for.

It helps humans see the big picture fast.

## Why does the notebook care about categories, app names, and reviewers?

Because the same app name can sometimes appear in different categories.

If the notebook only used the app name, it could accidentally connect the wrong folder link to the wrong app.

So it keeps track of:

- category,
- app name,
- reviewer.

That is like writing both the student’s name and classroom on a paper, instead of only writing “Alex,” because there might be many Alexes.

## What should a human do when using this notebook?

A normal human flow looks like this:

1. Open the notebook in the `REVIEW-REPORT` folder.
2. Run Cell 1 and sign in.
3. Run Cell 2 and pick the apps to scan.
4. Run Cell 5 and wait for the scan to finish.
5. Read the dashboard.
6. Save reports if needed.
7. Run Cell 7 only if reminder emails should be prepared or sent.

## What can go wrong?

A few common things:

- login fails,
- SharePoint permissions are missing,
- the folder structure is not what the notebook expects,
- an Excel sheet has strange column names,
- the AD cache is missing,
- Cell 7 tries to send mail without the right sender permissions.

That is why the notebook keeps logs.

Logs are like a diary of what happened during the run.

## Why is this notebook useful?

Because reading lots of SharePoint folders and Excel files by hand is slow and boring.

This notebook helps people:

- see progress faster,
- avoid checking the same files over and over,
- export clean reports,
- remind the right reviewers,
- keep the review process moving.

So in simple words:

this notebook is the team’s smart clipboard for tracking who still needs to finish their access review work.
