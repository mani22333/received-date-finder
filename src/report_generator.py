"""CSV writers."""
import csv
from pathlib import Path

EXTRACTION_COLUMNS = ["filename", "extracted_date", "status", "original_date_text", "location", "reason"]
TEST_COLUMNS = ["test_id", "filename", "scenario", "expected_result", "actual_result", "status", "error_message"]


def _write(path, columns, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_extraction_report(results, path):
    _write(path, EXTRACTION_COLUMNS, [{
        "filename": r.filename, "extracted_date": r.date, "status": r.status,
        "original_date_text": r.original_date_text, "location": r.location, "reason": r.reason,
    } for r in results])


def write_test_report(rows, path):
    _write(path, TEST_COLUMNS, rows)


def write_simple_report(results, path):
    """Two columns only: filename, received_date (blank when no date could be given)."""
    _write(path, ["filename", "received_date"],
           [{"filename": r.filename, "received_date": r.date} for r in results])
