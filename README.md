# Dailies

A local, single-user contest-practice app: daily math and Python problems, exact answer checking, saved code drafts, external judge links, review, and progress tracking.

## Run on Windows

Requires Python 3.11 or newer. In this folder:

```powershell
python -m pip install --target .packages -r requirements.txt
./run.ps1
```

Open **http://127.0.0.1:8765**. Keep the terminal running. Stop with Ctrl+C. Everything is served by FastAPI; opening the HTML file directly will not work.

Alternatively, use a virtual environment and run `python -m uvicorn app:app --host 127.0.0.1 --port 8765`. The app intentionally binds to loopback and has no account system. It is not a production deployment.

## What works

- Daily sets are created on first access, based on your timezone, and remain stable for that date. SQLite transactions serialize concurrent creation.
- Defaults: two math problems and one coding problem, approximately 30 minutes. Workload and independent starting levels are configurable.
- Original in-app math includes numeric, multiple-choice, and self-reviewed proof formats. Fractions and finite decimals compare exactly, without evaluating expressions.
- Python drafts autosave to SQLite. Open DMOJ to read the source statement and manually submit; record the judge result here. No submitted code is executed by Dailies.
- Library filters, attempt history, topic statistics, optional review queue, and complete JSON export/restore.
- Assigned canonical problem identities never repeat automatically. Attempted library problems also stay out of fresh recommendations. Reviews do not create daily assignments.
- Recommendations adjust at most one level from your selected baseline using the most recent eight attempts, after at least five attempts. Assistance and perceived difficulty affect promotion. This is an initial heuristic, not a calibrated rating model.

## Starter catalog and provenance

The starter contains **30 original math exercises and 18 Waterloo CCC references**. It supplies at least 14 daily sets at the default settings. The math exercises emphasize foundations and reuse several structures with different parameters; this is a working pilot catalog, not yet a comprehensive Cayley/CSMC archive. They are labeled as Dailies Originals, not Waterloo questions. Each answer has a reproducible derivation in its solution.

CCC entries point to DMOJ and retain native J2/J3/J4 labels. No Waterloo statements or solutions are copied. DMOJ blocks automated direct reads in this environment; contest identities were cross-checked against publicly indexed DMOJ listings, but live judge availability is not guaranteed. See [SOURCE_REVIEW.md](SOURCE_REVIEW.md).

Completed-contest exclusions start with Cayley 2025, CIMC 2024, CCC Junior 2025, and all CSMC editions until you enter the actual CSMC year. These exclusions cover imported records whose contest labels follow the same naming convention.

## Import reviewed problems

Exported backups include the complete catalog and can serve as a format reference. Imports accept a JSON array of problem objects with the exact same fields as `catalog.py`. All statements render as plain text. For mathematical notation, use Unicode and readable text in this pilot.

```powershell
$env:PYTHONPATH = "$PWD/.packages"
python manage.py import-catalog candidate-problems.json
# Review provenance, answer keys, canonical identities, difficulty, and the summary first.
python manage.py import-catalog candidate-problems.json --approve
```

The first command validates only. The second explicitly activates the reviewed import as supplied. Imports only add new IDs; they never silently overwrite history. Active math must have approved/original content, a verified key, and a solution. `reference_only` records must contain no statement, solution, or answer. Set the same canonical ID for known mirrors; all mirrors are excluded after one is assigned. Verification flags represent the curator's review, not automatic mathematical proof.

Codeforces metadata can be staged using the official API:

```powershell
python manage.py fetch-codeforces codeforces-candidates.json
```

Staged records are inactive. Review, choose a subset, correct topic/difficulty mappings, set `active` to `true`, then use the validation/approval commands. Network failures never change the catalog. Waterloo, DMOJ, USACO, USACO Guide, and textbooks currently enter through the reviewed JSON import contract; dedicated automated adapters for those sources remain future work.

## Data and checks

Database: `data/dailies.sqlite3` (created automatically and excluded from Git). Backup files contain personal practice data; keep them private. Restore replaces current data within a transaction and rolls back on invalid references. Export before restoring if you need the current history.

```powershell
$env:PYTHONPATH = "$PWD/.packages"
python -m unittest -v
```

Tests cover concurrent daily generation, persistence, 14-day capacity, shortages, exact math checks, exclusions, timezone boundaries, draft and backup restoration, invalid import rollback, review separation, and adaptation. No cloud sync, background notifications, AI grading, automatic judge submission, or code execution is included.

## Next milestones

1. Expand the math catalog with distinct contest-level problems and reviewed reuse permissions.
2. Add source adapters and curated topic/difficulty mapping for Waterloo, DMOJ, USACO, and USACO Guide.
3. Add diagnostic onboarding and refine recommendations from real practice results.
4. Add authenticated private hosting and cross-device sync before public access.

## Euclid goal update

The math track now targets a personal goal of **75/100 on Euclid**. Distinction is the top 25% of competitors, not a fixed score threshold ([CEMC](https://cemc.uwaterloo.ca/contests/euclid)). This is a practice goal, not a score prediction.

The catalog includes **28 additional original Euclid-preparation problems**: 14 core and 14 stretch, with worked solutions. These are unofficial estimated bands, not past Waterloo questions or calibrated Euclid question numbers. Independent enumeration tests check several counting and number-theory answer keys. Numeric marking checks the final answer only; write out reasoning separately and compare it with the solution.

Default math level is now 4. At this level, daily selection alternates a level-4 core problem with a level-5 stretch problem. Basic starter drills stay accessible in the library but are excluded from daily sets at math levels 3 and above. There are two weeks of fresh Euclid math pairs. Once these run out, the app reports a shortage instead of reverting to basic drills. Estimated daily time is now about **41 minutes** including coding; adjust the workload in Settings if needed.

For an existing database, `python upgrade_euclid.py` explicitly sets the math baseline to 4 and replaces only today's unattempted basic math assignments. It first saves a local JSON backup. Superseded assignment identities remain in the database and exports, preventing accidental reassignment. Coding and attempted problems are preserved. Do not rerun the command if you have intentionally chosen a different math baseline.
