# HiringFlow — Hiring Workflow & Data Quality System

A reproducible, synthetic hiring-workflow dataset and validation pipeline built for the 72 Hours Code Challenge. It generates related hiring entities, stores them in SQLite, exports CSV/JSON, preserves application-stage history, and keeps deliberate anomaly labels in a separate `ground_truth` dataset.

> All names, emails, requisitions, candidates, interviews, and compensation values are synthetic. The `example.test` email domain is intentionally non-deliverable. No real candidate data is used.

## What it covers

- Requisitions and hiring managers
- Candidate profiles and applications
- Role-specific skill requirements
- Interview panels, interviewer availability, and scheduled interviews
- Structured scorecards with derived overall scores
- Offers and approvals linked to compensation bands
- Append-only application-stage event history
- Five labelled edge cases: stage gate violation, interviewer double-booking, offer above band, withdrawn candidate still scheduled, and irrelevant scorecard criterion
- CSV/JSON exports, SQLite database, validation summary, and source manifest with SHA-256 checksums

## Requirements

- Python 3.10 or newer
- pip
- Git (only needed for GitHub submission)

## Windows setup (PowerShell)

Open PowerShell in the project folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, use this command for the current terminal only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

You can also skip activation and run `.venv\Scripts\python.exe` directly.

## Generate a starter dataset

```powershell
python -m src.hiringflow.generator --scale starter --seed 20261022
```

This creates a small dataset for a fast first run. Generated files appear in `output/`.

## Generate the full assignment volume

```powershell
python -m src.hiringflow.generator --scale full --seed 20261022
```

The full profile targets 200 requisitions, 5,000 candidates, 8,000 applications, and 2,000 interviews. Supporting tables scale from those parent records. It can take longer than the starter run.

To write results to another folder:

```powershell
python -m src.hiringflow.generator --scale starter --seed 20261022 --output output_demo
```

## See the output

- `output/csv/` — one CSV per entity/table
- `output/json/` — one JSON array per entity/table
- `output/hiringflow.sqlite` — queryable local database
- `output/schema.sql` — logical relational schema and constraints
- `output/validation_summary.csv` — checks and pass/fail status
- `output/source_manifest.json` — seed, row counts, checksums, and validation summary

`ground_truth.csv` and `ground_truth.json` are deliberately separate from normal business tables. They identify known synthetic exception cases and document the expected decision. Do not use ground-truth labels as input features if you later build a classifier.

## Query the SQLite database

Use DB Browser for SQLite or Python. Example Python query:

```powershell
python -c "import sqlite3; c=sqlite3.connect('output/hiringflow.sqlite'); print(c.execute('SELECT current_stage, COUNT(*) FROM applications GROUP BY current_stage ORDER BY current_stage').fetchall()); c.close()"
```

Example: find offers outside their recorded band:

```sql
SELECT offer_id, proposed_salary_inr, salary_min_inr, salary_max_inr, offer_status, issue_type
FROM offers
WHERE proposed_salary_inr < salary_min_inr OR proposed_salary_inr > salary_max_inr;
```

Example: find interviewers assigned to more than one interview at the same date and start time:

```sql
SELECT interviewer_id, scheduled_date, start_time, COUNT(*) AS interview_count
FROM interviews
WHERE status IN ('SCHEDULED', 'RESCHEDULED')
GROUP BY interviewer_id, scheduled_date, start_time
HAVING COUNT(*) > 1;
```

## Run tests

```powershell
python -m pytest -q
```

## Reproducibility check

Generate the same scale twice into separate folders and compare manifests/checksums:

```powershell
python -m src.hiringflow.generator --scale starter --seed 20261022 --output output_run_a
python -m src.hiringflow.generator --scale starter --seed 20261022 --output output_run_b
```

The generated data files should have identical SHA-256 checksums for the same seed and scale. The manifest intentionally does not include a generation timestamp because that would make it differ across runs.

## Data model and relationships

See [`docs/data_dictionary.md`](docs/data_dictionary.md) and [`output/schema.sql`](output/schema.sql). Primary keys are immutable deterministic IDs. Foreign-key relationships are validated before reviewing business exceptions. Many-to-many relationships are represented by rows in bridge-style tables where applicable (for example, skill requirements per requisition and interviewer availability entries).

## Known scope notes

This is a synthetic-data and business-rule prototype, not a production ATS. It does not send emails, connect to calendars, or make real hiring decisions. Interview scheduling is generated deterministically with conflict avoidance in the baseline and a labelled negative case for validation. The included `ground_truth` file is evaluation metadata, not operational source data.
