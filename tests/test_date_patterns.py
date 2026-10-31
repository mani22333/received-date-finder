import unittest

from src.config import DEFAULT_POLICY
from src.date_patterns import match_date_at, normalize_text, received_label_regex, label_boundary_ok
from src.date_extractor import scan_text


class DateShapeTests(unittest.TestCase):
    def test_shapes(self):
        cases = {
            "12 March 2024": "dmy_name", "12th Mar 24": "dmy_name", "12-Mar-2024": "dmy_name",
            "March 12, 2024": "mdy_name", "Mar 12 2024": "mdy_name", "2024-03-12": "iso",
            "2024/03/12": "iso", "20240312": "compact", "12/03/2024": "numeric", "12.03.24": "numeric",
            "March 2024": "month_year", "12 March": "day_month", "2024": "year_only",
            "Tuesday, 12 March 2024": "dmy_name", "4th Sept. 2026": "dmy_name",
        }
        for text, kind in cases.items():
            with self.subTest(text):
                raw = match_date_at(text)
                self.assertIsNotNone(raw)
                self.assertEqual(raw.kind, kind)

    def test_not_dates(self):
        for text in ["soon", "", "funding on 5 June", "marzo 2024", "N/A"]:
            with self.subTest(text):
                self.assertIsNone(match_date_at(text))

    def test_normalize(self):
        self.assertEqual(normalize_text("12\u00a0 March\u200b  2024"), "12 March 2024")
        self.assertEqual(normalize_text("2024\u201303\u201312"), "2024-03-12")
        self.assertEqual(normalize_text("Rec\u2019d"), "Rec'd")


class LabelTests(unittest.TestCase):
    def labels(self, text, **kw):
        rx = received_label_regex(**kw)
        return [m.group(0) for m in rx.finditer(text) if label_boundary_ok(text, m.start())]

    def test_label_variants(self):
        for text in ["Received", "Date received", "DATE RECEIVED", "Manuscript received on", "Rec'd", "Recd", "Rcvd",
                     "received", "Date of receipt"]:
            with self.subTest(text):
                self.assertEqual(len(self.labels(text + ": 1 Jan 2024")), 1)

    def test_not_labels(self):
        for text in ["We received funding", "The team received support", "Accepted: 1 Jan 2024",
                     "Received in revised form: 1 Jan 2024", "Preceded by", "Resubmitted: 1 Jan 2024"]:
            with self.subTest(text):
                self.assertEqual(self.labels(text), [])

    def test_submitted_only_with_policy(self):
        self.assertEqual(self.labels("Submitted: 1 Jan 2024"), [])
        self.assertEqual(len(self.labels("Submitted: 1 Jan 2024", submitted_counts=True)), 1)
        self.assertEqual(self.labels("Resubmitted: 1 Jan 2024", submitted_counts=True), [])

    def test_scan_text_kinds(self):
        kinds = lambda t: [h.kind for h in scan_text(t, DEFAULT_POLICY)]
        self.assertEqual(kinds("Received: 2 Jan 2026; Revised: 4 Mar 2026"), ["date"])
        self.assertEqual(kinds("Received:"), ["label_only"])
        self.assertEqual(kinds("Received: soon"), ["garbage"])
        self.assertEqual(kinds("Received funding on 5 June 2023 from the council"), [])
        self.assertEqual(kinds("Received 2 Jan 2026; Received in revised form 4 Mar 2026"), ["date"])


if __name__ == "__main__":
    unittest.main()
