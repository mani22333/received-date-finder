"""Scenario table: every row is one scenario from the Scenario List.

Each row is run by tests/scenario_runner.py (CSV report) and by
tests/test_scenarios.py (one test per row). Expected values come from the
scenario list / the actual sample documents, never from the tool's output.
"""
from collections import namedtuple
from dataclasses import replace
from datetime import date

from src.config import (AMBIGUOUS, DEFAULT_POLICY, FILE_ERROR, INVALID_DATE, MULTIPLE_DATES,
                        NOT_FOUND, SUCCESS)

TODAY = date(2026, 10, 31)  # fixed "today" so results never change

# id, group, description, expected (status, iso-date), spec for the factory,
# raw=(filename, bytes) for non-docx inputs, policy override
S = namedtuple("S", "id group desc expected spec raw policy")


def sc(id, group, desc, expected, spec=None, raw=None, policy=None):
    return S(id, group, desc, expected, spec, raw, policy)


def rec(text, label="Received: "):
    return {"body": ["Title of the paper", f"{label}{text}", "Some abstract text."]}


OK = lambda d: (SUCCESS, d)
D = "2024-03-12"
SCENARIOS = []
add = SCENARIOS.append

# ---- B. positive: date formats -------------------------------------------------
for i, (txt, exp) in enumerate([
    ("12 March 2024", OK(D)), ("March 12, 2024", OK(D)), ("12 Mar 2024", OK(D)), ("Mar 12 2024", OK(D)),
    ("12th March 2024", OK(D)), ("12th Mar 24", OK(D)), ("2024-03-12", OK(D)), ("2024/03/12", OK(D)),
    ("25/03/2024", OK("2024-03-25")), ("03/25/2024", OK("2024-03-25")), ("25-03-2024", OK("2024-03-25")),
    ("25.03.2024", OK("2024-03-25")), ("20240312", OK(D)), ("Tuesday, 12 March 2024", OK(D)),
    ("12-Mar-2024", OK(D)), ("12 March 2024, 10:30 AM", OK(D)), ("12\u00a0March\u00a02024", OK(D)),
    ("12   March    2024", OK(D)), ("12 MARCH 2024", OK(D)), ("12 march 2024", OK(D)),
    ("2 March 2024", OK("2024-03-02")), ("02 March 2024", OK("2024-03-02")), ("1st March 2024", OK("2024-03-01")),
    ("2nd March 2024", OK("2024-03-02")), ("3rd March 2024", OK("2024-03-03")), ("4th March 2024", OK("2024-03-04")),
    ("22nd March 2024", OK("2024-03-22")), ("12 March, 2024", OK(D)), ("12-03-2024", (AMBIGUOUS, "")),
    ("12/03/2024", (AMBIGUOUS, "")), ("12.03.2024", (AMBIGUOUS, "")),
], 1):
    add(sc(f"POS-FMT-{i:02d}", "positive/format", f"Received: {txt!r}", exp, rec(txt)))

# ---- B. positive: labels ---------------------------------------------------------
for i, (label, exp) in enumerate([
    ("Received ", OK(D)), ("Date received: ", OK(D)), ("Date Received: ", OK(D)), ("Manuscript received on ", OK(D)),
    ("Received on ", OK(D)), ("Rec'd ", OK(D)), ("Rec\u2019d: ", OK(D)), ("Recd. ", OK(D)), ("Rcvd: ", OK(D)),
    ("RECEIVED: ", OK(D)), ("received: ", OK(D)), ("Received - ", OK(D)), ("Received \u2013 ", OK(D)),
    ("Received\u2014", OK(D)), ("Date of receipt: ", OK(D)), ("Article history: Received: ", OK(D)),
], 1):
    add(sc(f"POS-LBL-{i:02d}", "positive/label", f"Label {label!r}", exp, rec("12 March 2024", label)))
add(sc("POS-LBL-17", "positive/label", "Label and date in separate paragraphs", OK(D),
       {"body": ["Title", "Received", "12 March 2024", "Accepted", "10 May 2024"]}))
add(sc("POS-LBL-18", "positive/label", "Label and date separated by a line break", OK(D),
       {"body": [("br", ["Received:", "12 March 2024"])]}))

# ---- B. positive: locations -------------------------------------------------------
add(sc("POS-LOC-01", "positive/location", "First-page body", OK(D), rec("12 March 2024")))
add(sc("POS-LOC-02", "positive/location", "Header", OK(D), {"body": ["Title"], "header": ["Received: 12 March 2024"]}))
add(sc("POS-LOC-03", "positive/location", "Footer", OK(D), {"body": ["Title"], "footer": ["Received: 12 March 2024"]}))
add(sc("POS-LOC-04", "positive/location", "Table: label cell then date cell", OK(D),
       {"body": ["Title", ("table", [["Accepted", "10 May 2024"], ["Received", "12 March 2024"]])]}))
add(sc("POS-LOC-05", "positive/location", "Table: label and date in the same cell", OK(D),
       {"body": [("table", [["Received: 12 March 2024", "x"]])]}))
add(sc("POS-LOC-06", "positive/location", "Nested table", OK(D),
       {"body": [("table", [[("table", [["Received", "12 March 2024"]]), "x"]])]}))
add(sc("POS-LOC-07", "positive/location", "Text box", OK(D), {"body": ["Title", ("textbox", "Received: 12 March 2024")]}))
add(sc("POS-LOC-08", "positive/location", "Footnote", OK(D), {"body": ["Title"], "footnotes": ["Received: 12 March 2024"]}))
add(sc("POS-LOC-09", "positive/location", "Endnote", OK(D), {"body": ["Title"], "endnotes": ["Received: 12 March 2024"]}))
add(sc("POS-LOC-10", "positive/location", "Comment", OK(D), {"body": ["Title"], "comments": ["Received: 12 March 2024"]}))
add(sc("POS-LOC-11", "positive/location", "Tracked insertion is read", OK(D), {"body": [("ins", "Received: 12 March 2024")]}))
add(sc("POS-LOC-12", "positive/location", "Date split across formatting runs", OK(D),
       {"body": [("runs", ["Rece", "ived: 12 Ma", "rch 20", "24"])]}))
add(sc("POS-LOC-13", "positive/location", "Label in header, date in header next paragraph", OK(D),
       {"body": ["Title"], "header": ["Received", "12 March 2024"]}))

# ---- B. positive: mixed layouts ---------------------------------------------------
add(sc("POS-MIX-01", "positive/mixed", "Received, accepted and published in one line", OK(D),
       {"body": ["Received: 12 Mar 2024; Accepted: 10 May 2024; Published: 1 Jun 2024"]}))
add(sc("POS-MIX-02", "positive/mixed", "Received appears after the other dates", OK(D),
       {"body": ["Accepted: 10 May 2024", "Revised: 1 Apr 2024", "Received: 12 March 2024"]}))
add(sc("POS-MIX-03", "positive/mixed", "Same received date written twice (different formats)", OK(D),
       {"body": ["Received: 12 March 2024"], "header": ["Received 2024-03-12"]}))
add(sc("POS-MIX-04", "positive/mixed", "Pipe-separated header with other dates", OK(D),
       {"body": ["Title"], "header": ["Received 12 Mar 2024 | Accepted 10 May 2024 | Contributions: A.B."]}))
add(sc("POS-MIX-05", "positive/mixed", "Received then 'Received in revised form' (only first counts)", OK(D),
       {"body": ["Received 12 March 2024; Received in revised form 4 June 2024; Accepted 1 July 2024"]}))
add(sc("POS-MIX-06", "positive/mixed", "Received label only after the reference list", OK(D),
       {"body": ["References", "[1] Smith J. A paper. J Test. 2019;1:1-2.", "Received: 12 March 2024"]}))

add(sc("POS-MIX-07", "positive/mixed", "Label right after a sentence end in the same paragraph", OK(D),
       {"body": ["The manuscript was reviewed. Received: 12 March 2024. Accepted: 1 June 2024."]}))
add(sc("POS-MIX-08", "positive/mixed", "Label in parentheses", OK(D), {"body": ["(Received 12 March 2024)"]}))
add(sc("POS-MIX-09", "positive/mixed", "Bullet before label", OK(D), {"body": ["\u2022 Received: 12 March 2024"]}))

# ---- C. negative ----------------------------------------------------------------------
NF = (NOT_FOUND, "")
for i, (txt) in enumerate([
    "Accepted: 10 May 2024", "Revised: 10 May 2024", "Published: 10 May 2024", "Submitted: 10 May 2024",
    "Resubmitted: 10 May 2024", "Published online: 10 May 2024", "Available online 10 May 2024",
    "Accepted 10 May 2024; Revised 1 April 2024; Published online 1 June 2024",
    "Received in revised form: 10 May 2024",
], 1):
    add(sc(f"NEG-OTHER-{i:02d}", "negative", f"Only a non-received date: {txt}", NF, {"body": ["Title", txt]}))
add(sc("NEG-01", "negative", "Date with no label at all", NF, {"body": ["Title", "12 March 2024"]}))
add(sc("NEG-02", "negative", "No dates in the document", NF, {"body": ["Title", "Some text only."]}))
add(sc("NEG-03", "negative", "Empty document", NF, {"body": []}))
add(sc("NEG-04", "negative", "Label present but nothing after it", NF, {"body": ["Title", "Received:", "Accepted: 10 May 2024"]}))
add(sc("NEG-05", "negative", "'received' in a normal sentence (funding)", NF,
       {"body": ["We received funding on 5 June 2023 from the council."]}))
add(sc("NEG-06b", "negative", "Sentence ending then 'Received funding on <date>' prose", NF,
       {"body": ["The work was supported. Received funding on 5 June 2023 from the council."]}))
add(sc("NEG-06", "negative", "'received' in a sentence about samples", NF,
       {"body": ["The team received 120 samples on 5 May 2025."]}))
add(sc("NEG-07", "negative", "Grant / ethics approval date near the word received", NF,
       {"body": ["Ethics approval was received on 3 February 2023. Grant awarded 4 March 2023."]}))
add(sc("NEG-08", "negative", "Received date inside a cited reference", NF,
       {"body": ["References", "[1] Smith J. A paper. J Test. 2019. Received 12 March 2019."]}))
add(sc("NEG-09", "negative", "Submitted is not treated as received (default policy)", NF, {"body": ["Submitted: 12 March 2024"]}))
for i, txt in enumerate(["31 February 2024", "32/01/2024", "13/13/2024", "00/03/2024", "12/00/2024", "2024-13-01",
                         "2024-02-30", "Received 12 Foo 2024"][:7], 1):
    add(sc(f"NEG-INV-{i:02d}", "negative/invalid", f"Invalid date {txt!r}", (INVALID_DATE, ""), rec(txt)))
add(sc("NEG-INV-08", "negative/invalid", "Nonsense after label ('soon')", (INVALID_DATE, ""), rec("soon")))
add(sc("NEG-INV-09", "negative/invalid", "Month and year only", (INVALID_DATE, ""), rec("March 2024")))
add(sc("NEG-INV-10", "negative/invalid", "Year only", (INVALID_DATE, ""), rec("2024")))
add(sc("NEG-INV-11", "negative/invalid", "Day and month only", (INVALID_DATE, ""), rec("12 March")))
add(sc("NEG-INV-12", "negative/invalid", "Future date", (INVALID_DATE, ""), rec("12 March 2031")))
add(sc("NEG-INV-13", "negative/invalid", "Date before sensible year (1800)", (INVALID_DATE, ""), rec("12 March 1800")))
add(sc("NEG-INV-14", "negative/invalid", "Non-English month name (unsupported)", (INVALID_DATE, ""), rec("12 marzo 2024")))
add(sc("NEG-CONF-01", "negative/conflict", "Two different received dates", (MULTIPLE_DATES, ""),
       {"body": ["Received: 12 March 2024"], "header": ["Received: 13 March 2024"]}))
add(sc("NEG-CONF-02", "negative/conflict", "One valid and one invalid received entry", (MULTIPLE_DATES, ""),
       {"body": ["Received: 12 March 2024", "Received: 31 February 2024"]}))
for i, (fn, data) in enumerate([("paper.pdf", b"%PDF-1.4 fake"), ("paper.txt", b"Received: 12 March 2024"),
                                ("paper.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"x" * 50),
                                ("paper.dotx", b"PK\x03\x04"), ("paper.docx", b"this is not a zip file at all"),
                                ("encrypted.docx", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"x" * 50),
                                ("empty.docx", b""), ("~$paper.docx", b"x" * 20),
                                ("truncated.docx", b"PK\x03\x04" + b"\x00" * 20)], 1):
    add(sc(f"NEG-FILE-{i:02d}", "negative/file", f"Bad input file {fn}", (FILE_ERROR, ""), raw=(fn, data)))
add(sc("NEG-FILE-10", "negative/file", "File not found", (FILE_ERROR, ""), raw=("__missing__.docx", None)))
add(sc("NEG-FILE-11", "negative/file", "Path is a folder", (FILE_ERROR, ""), raw=("__folder__.docx", "DIR")))

# ---- D. boundary -------------------------------------------------------------------------
add(sc("BND-01", "boundary", "Leap day 29 Feb 2024 is valid", OK("2024-02-29"), rec("29 Feb 2024")))
add(sc("BND-02", "boundary", "29 Feb 2023 is invalid", (INVALID_DATE, ""), rec("29 Feb 2023")))
add(sc("BND-03", "boundary", "First day of year", OK("2024-01-01"), rec("01 Jan 2024")))
add(sc("BND-04", "boundary", "Last day of year", OK("2024-12-31"), rec("31 Dec 2024")))
add(sc("BND-05", "boundary", "31 April is invalid", (INVALID_DATE, ""), rec("31 April 2024")))
add(sc("BND-06", "boundary", "30 April is valid", OK("2024-04-30"), rec("30 April 2024")))
add(sc("BND-07", "boundary", "Year 1999 accepted", OK("1999-12-31"), rec("31 Dec 1999")))
add(sc("BND-08", "boundary", "Year 2000 accepted", OK("2000-01-01"), rec("1 Jan 2000")))
add(sc("BND-09", "boundary", "Year 2099 rejected as future", (INVALID_DATE, ""), rec("1 Jan 2099")))
add(sc("BND-10", "boundary", "Two-digit year 99 -> 1999 (pivot 69, flagged)", OK("1999-03-12"), rec("12 Mar 99")))
add(sc("BND-11", "boundary", "Two-digit year 00 -> 2000", OK("2000-03-12"), rec("12 Mar 00")))
add(sc("BND-12", "boundary", "Two-digit year 24 -> 2024", OK(D), rec("12 Mar 24")))
add(sc("BND-13", "boundary", "Two-digit year unresolved when pivot rule switched off", (AMBIGUOUS, ""), rec("12 Mar 24"),
       policy=replace(DEFAULT_POLICY, two_digit_year_pivot=None)))
add(sc("BND-14", "boundary", "Ambiguous 03/04/2024 is not guessed", (AMBIGUOUS, ""), rec("03/04/2024")))
add(sc("BND-15", "boundary", "25/03/2024: only day-first is real", OK("2024-03-25"), rec("25/03/2024")))
add(sc("BND-16", "boundary", "05/05/2024: both readings equal", OK("2024-05-05"), rec("05/05/2024")))
add(sc("BND-17", "boundary", "Date at the very first paragraph", OK(D), {"body": ["Received: 12 March 2024", "text"]}))
add(sc("BND-18", "boundary", "Date at the very last paragraph", OK(D), {"body": ["text"] * 5 + ["Received: 12 March 2024"]}))
add(sc("BND-19", "boundary", "Very long document (3000 paragraphs), date last", OK(D),
       {"body": ["Lorem ipsum dolor sit amet. " * 20] * 3000 + ["Received: 12 March 2024"]}))
add(sc("BND-20", "boundary", "Very long paragraph around the date", OK(D),
       {"body": ["Preface text " * 2000 + "; Received: 12 March 2024; " + "Trailing text " * 2000]}))
add(sc("BND-21", "boundary", "Month forms Sept / Sep / September", OK("2024-09-12"),
       {"body": ["Received: 12 Sept 2024"]}))
add(sc("BND-22", "boundary", "Month form Sep.", OK("2024-09-12"), {"body": ["Received: 12 Sep. 2024"]}))
add(sc("BND-23", "boundary", "Special dashes in ISO date", OK(D), rec("2024\u201303\u201312")))
add(sc("BND-24", "boundary", "Zero-width characters inside the date", OK(D), rec("12 Mar\u200bch 2024")))
add(sc("BND-25", "boundary", "Date in a deeply nested table", OK(D),
       {"body": [("table", [[("table", [[("table", [["Received", "12 March 2024"]])]]), "x"]])]}))
add(sc("BND-26", "boundary", "Tracked deletion is ignored", NF, {"body": [("del", "Received: 12 March 2024")]}))
add(sc("BND-27", "boundary", "Text in 1000-cell table", OK(D),
       {"body": [("table", [["c"] * 10 for _ in range(100)]), "Received: 12 March 2024"]}))

# ---- policy-dependent scenarios (open product-owner questions) -------------------------------
P = DEFAULT_POLICY
add(sc("POL-01", "policy", "day_first policy: 03/04/2024 -> 3 April", OK("2024-04-03"), rec("03/04/2024"),
       policy=replace(P, ambiguous_numeric="day_first")))
add(sc("POL-02", "policy", "month_first policy: 03/04/2024 -> 4 March", OK("2024-03-04"), rec("03/04/2024"),
       policy=replace(P, ambiguous_numeric="month_first")))
add(sc("POL-03", "policy", "chronology policy resolves 03/04/2024 using revised/accepted", OK("2024-03-04"),
       {"body": ["Received: 03/04/2024", "Revised: 12 March 2024", "Accepted: 28 March 2024"]},
       policy=replace(P, ambiguous_numeric="chronology")))
add(sc("POL-04", "policy", "chronology policy stays AMBIGUOUS when both readings fit", (AMBIGUOUS, ""),
       {"body": ["Received: 03/04/2026; Revised: 05/06/2026; Accepted: 07/08/2026"]},
       policy=replace(P, ambiguous_numeric="chronology")))
two = {"body": ["Received: 12 March 2024", "Received: 13 March 2024"]}
add(sc("POL-05", "policy", "multiple_received=first", OK(D), two, policy=replace(P, multiple_received="first")))
add(sc("POL-06", "policy", "multiple_received=latest", OK("2024-03-13"), two, policy=replace(P, multiple_received="latest")))
add(sc("POL-07", "policy", "submitted_is_received=True", OK(D), {"body": ["Submitted: 12 March 2024"]},
       policy=replace(P, submitted_is_received=True)))
add(sc("POL-08", "policy", "Resubmitted never counts even when submitted does", NF, {"body": ["Resubmitted: 12 March 2024"]},
       policy=replace(P, submitted_is_received=True)))
add(sc("POL-09", "policy", "received_in_revised_form_counts=True", OK(D), {"body": ["Received in revised form: 12 March 2024"]},
       policy=replace(P, received_in_revised_form_counts=True)))
add(sc("POL-10", "policy", "allow_future_dates=True accepts 2031", OK("2031-03-12"), rec("12 March 2031"),
       policy=replace(P, allow_future_dates=True)))
add(sc("POL-11", "policy", "include_deleted_text=True reads tracked deletions", OK(D),
       {"body": [("del", "Received: 12 March 2024")]}, policy=replace(P, include_deleted_text=True)))

# ---- real sample manuscripts: expected value read by hand from each document ---------------------
SAMPLES = {
    1: OK("2026-01-02"), 2: OK("2026-01-02"), 3: OK("2026-01-02"), 4: OK("2026-01-02"),
    5: (AMBIGUOUS, ""), 6: (AMBIGUOUS, ""), 7: (AMBIGUOUS, ""), 8: NF, 9: NF, 10: OK("2026-01-02"),
    11: OK("2026-01-02"), 12: (FILE_ERROR, ""), 13: OK("2026-01-02"), 14: OK("2026-01-02"),
    15: OK("2026-01-02"), 16: OK("2026-01-02"), 17: OK("2026-01-02"), 18: (AMBIGUOUS, ""),
    19: (INVALID_DATE, ""), 20: OK("2026-01-02"),
}
SAMPLE_NOTES = {
    1: "Received/Revised/Accepted in one line near the top", 2: "same, at the very end, full month names",
    3: "labels on separate lines, accepted/revised mixed in", 4: "Accepted first, Received at the end",
    5: "03/04/2026 ambiguous", 6: "03/04/2026 ambiguous (chronology would favour 4 March)",
    7: "03/04/2026 ambiguous; all dates numeric", 8: "only an Accepted date", 9: "no received label; 'we received' sentences",
    10: "plain labels", 11: "Received with Published online/Issue date", 12: "file is not a valid .docx",
    13: "date in header; footer has Published online", 14: "'Received in revised form' must not count",
    15: "label and date in table cells, ISO date", 16: "Revised (round 2) must not count", 17: "prose with 'received/accepted/revised' dates",
    18: "12/05/26 ambiguous + 2-digit year; accepted 2031", 19: "31/04/2026 is not a real date", 20: "ordinal day, 'Sept.', dotted date",
}
