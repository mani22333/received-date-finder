import unittest
from dataclasses import replace
from datetime import date

from src.config import AMBIGUOUS, DEFAULT_POLICY, INVALID_DATE, SUCCESS
from src.date_patterns import match_date_at
from src.date_validator import interpret

TODAY = date(2026, 10, 31)


def run(text, policy=DEFAULT_POLICY):
    return interpret(match_date_at(text), policy, TODAY)


class ValidatorTests(unittest.TestCase):
    def test_valid(self):
        for text, iso in [("12 March 2024", "2024-03-12"), ("March 12, 2024", "2024-03-12"),
                          ("2024-03-12", "2024-03-12"), ("20240312", "2024-03-12"),
                          ("29 Feb 2024", "2024-02-29"), ("25/03/2024", "2024-03-25"),
                          ("03/25/2024", "2024-03-25"), ("05/05/2024", "2024-05-05")]:
            with self.subTest(text):
                o = run(text)
                self.assertEqual((o.status, o.date.isoformat()), (SUCCESS, iso))

    def test_invalid(self):
        for text in ["31 February 2024", "29 Feb 2023", "31 April 2024", "32/01/2024", "13/13/2024",
                     "00/03/2024", "2024-13-01", "2024-00-10", "March 2024", "2024", "12 March"]:
            with self.subTest(text):
                self.assertEqual(run(text).status, INVALID_DATE)

    def test_ambiguous_lists_both_readings(self):
        o = run("03/04/2024")
        self.assertEqual(o.status, AMBIGUOUS)
        self.assertEqual([d.isoformat() for d in o.readings], ["2024-04-03", "2024-03-04"])

    def test_ambiguity_is_decided_by_calendar_only(self):
        self.assertEqual(run("12/05/26").status, AMBIGUOUS)   # the future reading must not silently decide it

    def test_two_digit_year(self):
        self.assertEqual(run("12 Mar 24").date, date(2024, 3, 12))
        self.assertEqual(run("12 Mar 99").date, date(1999, 3, 12))
        self.assertTrue(any("two-digit" in w for w in run("12 Mar 24").warnings))
        self.assertEqual(run("12 Mar 24", replace(DEFAULT_POLICY, two_digit_year_pivot=None)).status, AMBIGUOUS)

    def test_range_rules(self):
        self.assertEqual(run("12 March 2031").status, INVALID_DATE)
        self.assertEqual(run("12 March 1800").status, INVALID_DATE)
        self.assertEqual(run("12 March 2031", replace(DEFAULT_POLICY, allow_future_dates=True)).status, SUCCESS)
        self.assertEqual(run("31 Dec 2026").status, INVALID_DATE)      # after the fixed 'today'
        self.assertEqual(run("31 Oct 2026").status, SUCCESS)           # today itself is allowed


if __name__ == "__main__":
    unittest.main()
