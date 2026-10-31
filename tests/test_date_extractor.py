import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.config import (AMBIGUOUS, DEFAULT_POLICY, FILE_ERROR, INVALID_DATE, MULTIPLE_DATES, NOT_FOUND, SUCCESS)
from src.date_extractor import extract_received_date
from tests.docx_factory import make_docx

TODAY = date(2026, 10, 31)


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def run_spec(self, spec, policy=DEFAULT_POLICY):
        return extract_received_date(make_docx(self.dir / "t.docx", spec), policy, TODAY)

    def test_does_not_take_the_first_date(self):
        r = self.run_spec({"body": ["Accepted: 10 April 2026", "Revised: 4 March 2026", "Received: 2 January 2026"]})
        self.assertEqual((r.status, r.date), (SUCCESS, "2026-01-02"))

    def test_other_dates_are_not_picked(self):
        for other in ["Accepted: 10 Apr 2026", "Revised: 10 Apr 2026", "Published online: 10 Apr 2026",
                      "Submitted: 10 Apr 2026", "Resubmitted: 10 Apr 2026", "Available online 10 Apr 2026"]:
            with self.subTest(other):
                self.assertEqual(self.run_spec({"body": [other]}).status, NOT_FOUND)

    def test_not_found_reason_mentions_other_dates(self):
        r = self.run_spec({"body": ["Accepted: 10 Apr 2026"]})
        self.assertIn("accepted", r.reason)

    def test_same_date_twice_is_one_result(self):
        r = self.run_spec({"body": ["Received: 12 March 2024"], "footer": ["Received 2024-03-12"]})
        self.assertEqual((r.status, r.date), (SUCCESS, "2024-03-12"))

    def test_conflicting_dates_are_reported_not_chosen(self):
        r = self.run_spec({"body": ["Received: 12 March 2024", "Received: 13 March 2024"]})
        self.assertEqual((r.status, r.date), (MULTIPLE_DATES, ""))
        self.assertIn("12 March 2024", r.original_date_text)
        self.assertIn("13 March 2024", r.original_date_text)

    def test_location_is_reported(self):
        self.assertIn("header", self.run_spec({"body": ["x"], "header": ["Received: 12 March 2024"]}).location)
        self.assertIn("table", self.run_spec({"body": [("table", [["Received", "12 March 2024"]])]}).location)

    def test_original_text_kept(self):
        r = self.run_spec({"body": ["Received: 12th Mar 24"]})
        self.assertEqual((r.original_date_text, r.date), ("12th Mar 24", "2024-03-12"))
        self.assertTrue(r.warnings)   # the two-digit year is flagged

    def test_ambiguity_hint_without_applying_it(self):
        r = self.run_spec({"body": ["Received: 03/04/2026", "Revised: 12 March 2026", "Accepted: 28 March 2026"]})
        self.assertEqual((r.status, r.date), (AMBIGUOUS, ""))
        self.assertIn("2026-03-04", r.reason)

    def test_extraction_never_raises(self):
        for name, data in [("a.docx", b"junk"), ("b.docx", b""), ("c.txt", b"x")]:
            p = self.dir / name
            p.write_bytes(data)
            self.assertEqual(extract_received_date(p, DEFAULT_POLICY, TODAY).status, FILE_ERROR)
        self.assertEqual(extract_received_date(self.dir / "missing.docx").status, FILE_ERROR)

    def test_deterministic(self):
        p = make_docx(self.dir / "d.docx", {"body": ["Received: 12 March 2024; Accepted: 1 June 2024"]})
        runs = {extract_received_date(p, DEFAULT_POLICY, TODAY).date for _ in range(5)}
        self.assertEqual(runs, {"2024-03-12"})

    def test_input_file_is_not_modified(self):
        import hashlib
        p = make_docx(self.dir / "m.docx", {"body": ["Received: 12 March 2024"]})
        before = hashlib.sha256(p.read_bytes()).hexdigest()
        extract_received_date(p, DEFAULT_POLICY, TODAY)
        self.assertEqual(before, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_invalid_beats_nothing(self):
        self.assertEqual(self.run_spec({"body": ["Received: 31/04/2026"]}).status, INVALID_DATE)


if __name__ == "__main__":
    unittest.main()
