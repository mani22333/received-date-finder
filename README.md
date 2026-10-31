# Received Date Finder (QE Hackathon, Problem 1)

Reads a manuscript Word file (`.docx`), finds the date it was **received**, and prints it as `YYYY-MM-DD`.
Rule-based and deterministic: no AI, no network, no guessing.

## Quick start

```bash
./run.sh                                   # set up, test, process input/, write reports
python main.py input/merged_01.docx        # one file -> 2026-01-02
python main.py input/                      # a whole folder -> output/extraction_report.csv
python main.py --write-test-report         # run all scenarios -> output/test_report.csv
```

Run the tests only: `python -m pytest tests` (or `python -m unittest discover -s tests -t .`).
Needs Python 3.9+, `python-docx`, `lxml` (and `pytest`, optional): `pip install -r requirements.txt`.

## How it works

```
document_reader  ->  date_extractor  ->  date_validator  ->  report_generator
 (all text, in        (label + date        (real calendar       (CSV files)
  document order)      matching)            date? range?)
```

1. **document_reader.py** opens the file with python-docx (validates it) and reads every text part from the raw XML:
   body, headers, footers, tables (including nested), text boxes, footnotes, endnotes, comments, tracked insertions.
   Text split across formatting runs is joined. python-docx alone cannot reach text boxes, notes or comments, so lxml is used.
2. **date_extractor.py** looks for a *received label* (`Received`, `Date received`, `Manuscript received on`, `Rec'd`, `Recd`, `Rcvd`,
   `Date of receipt`) that starts a line or follows `;` `|` `,` `(` `:` `.` and is followed by a date. If the label stands alone
   (a table cell, or its own paragraph) the date is taken from the next paragraph/cell. The first date in the document is never used.
3. **date_validator.py** checks the date against the calendar (leap years, 30/31-day months) and the allowed year range.
4. **report_generator.py** writes the CSVs. **date_patterns.py** holds all formats/labels. **config.py** holds statuses and the policy.

### Supported date formats
`12 March 2024`, `March 12, 2024`, `12 Mar 2024`, `12th Mar 24`, `12-Mar-2024`, `Tuesday, 12 March 2024`, `4th Sept. 2026`,
`2024-03-12`, `2024/03/12`, `20240312`, `12/03/2024`, `12-03-2024`, `12.03.2024`, any of these followed by a time.
Odd spaces (non-breaking, zero-width), Unicode dashes and curly apostrophes are normalised first. Month names: English only.

### What is NOT mistaken for a received date
Accepted, revised, published, published online, available online, issue date, submitted, resubmitted, **received in revised form**,
and prose such as "We received funding on 5 June 2023". Reference-list entries (`[1] ...`) are skipped.

## Statuses and output

| Status | Meaning | CLI stdout | Exit code |
|---|---|---|---|
| SUCCESS | one clear received date | `YYYY-MM-DD` only | 0 |
| NOT_FOUND | no received label with a date | `NOT_FOUND` | 1 |
| AMBIGUOUS | e.g. `03/04/2024` (day-first or month-first), or a 2-digit year with the rule switched off | `AMBIGUOUS` | 1 |
| INVALID_DATE | not a real date (`31/04/2026`), incomplete (`March 2024`), nonsense (`soon`), future, before 1990 | `INVALID_DATE` | 1 |
| MULTIPLE_DATES | two different received entries | `MULTIPLE_DATES` | 1 |
| FILE_ERROR | missing, wrong type, empty, corrupt, encrypted/old `.doc`, `~$` lock file | `FILE_ERROR` | 2 |

The reason always goes to stderr (single file) or the `reason` column (folder mode). The tool never crashes on a bad file.

## Open product-owner questions (policy in `src/config.py`)

None of these were confirmed, so the defaults are conservative. Change one field in `Policy` when the answer arrives.

| # | Question | Current default |
|---|---|---|
| 1 | `03/04/2024`: day-first or month-first? | **AMBIGUOUS** (both readings listed). Options: `day_first`, `month_first`, `chronology` |
| 2 | Two different received dates | **MULTIPLE_DATES**. Options: `first`, `latest` |
| 3 | Missing date output | status `NOT_FOUND`, exit code 1 |
| 4 | Is "Submitted" received? | No (`submitted_is_received`) |
| 5 | "Received in revised form" counts? | No (`received_in_revised_form_counts`) |
| 6 | Two-digit years | `00-69` = 20xx, `70-99` = 19xx, **flagged in the reason**. `None` = AMBIGUOUS |
| 7 | `.doc` / `.dotx` | Not supported, reported as FILE_ERROR |
| 8 | Folder mode with CSV | Supported (`python main.py <folder>`) |
| 9 | Year-only / month-only | INVALID_DATE |

`chronology` is available but **off**: for `03/04/2026` with `Revised: 12 March` and `Accepted: 28 March`, only 4 March is not later than the
other dates. The default reports AMBIGUOUS and mentions this as a hint (sample `merged_06`).

## Tests

* `tests/scenarios.py`: one row per scenario from the scenario list (formats, labels, locations, mixed layouts, negatives, boundaries,
  policies) plus the 20 sample manuscripts. Expected values are written by hand, never copied from the tool's output.
* `tests/test_scenarios.py` runs each row as its own test; `tests/scenario_runner.py` runs the same rows and writes `test_report.csv`.
* Unit tests: `test_date_patterns.py`, `test_date_validator.py`, `test_document_reader.py`, `test_date_extractor.py`; `test_integration.py` covers the
  samples and the command line (output format, exit codes, input file never modified, one report row per file).
* Synthetic `.docx` files are built by `tests/docx_factory.py` for anything the 20 samples do not cover (headers, footers, text boxes, notes,
  comments, tracked changes, nested tables, corrupt/empty/encrypted files).
* "Today" is fixed to 2026-10-31 in tests so the future-date rule gives the same result every day.

## Reports (`output/`, copy of `test_report.csv` in the repo root)

* `test_report.csv`: `test_id, filename, scenario, expected_result, actual_result, status, error_message`
* `received_dates.csv`: just `filename, received_date` (date is `YYYY-MM-DD`, blank when no date can be given)
* `extraction_report.csv`: `filename, extracted_date, status, original_date_text, location, reason` (one row per manuscript)

## Known limitations

* A date written to the **left** of its label in a table (`| 12 March 2024 | Received |`) is not found.
* Text inside a tracked **deletion** is ignored (policy `include_deleted_text`); tracked insertions are read.
* Dates drawn as pictures, in `.doc`/`.dotx`/PDF files, or in non-English month names are not supported (`12 marzo 2024` -> INVALID_DATE).
* Text boxes in older VML-only files and fields (`w:fldSimple` results) are read when their text is in `w:t`; field codes are ignored.
* A label with no `:`/`-` before a short non-date phrase (e.g. "Received funding.") is treated as prose and ignored.
* Password-protected files are reported as FILE_ERROR (they cannot be read), not decrypted.

## Website (upload files, see dates)

```bash
pip install -r requirements.txt
python app.py          # then open http://127.0.0.1:5000
```

Choose one or many `.docx` files, click **Find received dates**, read the table (file, date as `YYYY-MM-DD`, status, details) and
optionally download it as CSV. It uses the same extractor as `main.py`. Files are processed in a temporary folder and deleted afterwards.
It is meant for local use (127.0.0.1), not for the public internet.
