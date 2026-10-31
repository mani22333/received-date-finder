"""Statuses, exit codes and the POLICY section.

Every rule that the product owner has NOT confirmed yet lives in `Policy`.
Defaults are conservative: when a rule is open, the tool reports the problem
instead of guessing. Change one field here (or pass a different Policy) when
the product owner answers.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

SUCCESS = "SUCCESS"
NOT_FOUND = "NOT_FOUND"
AMBIGUOUS = "AMBIGUOUS"
INVALID_DATE = "INVALID_DATE"
MULTIPLE_DATES = "MULTIPLE_DATES"
FILE_ERROR = "FILE_ERROR"

# Command-line exit codes for a single file (0 only on SUCCESS).
EXIT_CODES = {
    SUCCESS: 0,
    NOT_FOUND: 1,
    AMBIGUOUS: 1,
    INVALID_DATE: 1,
    MULTIPLE_DATES: 1,
    FILE_ERROR: 2,
}


@dataclass(frozen=True)
class Policy:
    # 1. Ambiguous numeric dates such as 03/04/2024.
    #    'report'      -> status AMBIGUOUS, both readings listed (default)
    #    'day_first' / 'month_first' -> pick that reading (once PO confirms)
    #    'chronology'  -> pick the one reading that is not later than the
    #                     revised/accepted/published dates; else AMBIGUOUS
    ambiguous_numeric: str = "report"
    # 2. Two different received dates: 'report' | 'first' | 'latest'
    multiple_received: str = "report"
    # 4. Two-digit years: yy <= pivot -> 20yy, else 19yy. None -> AMBIGUOUS.
    #    Always flagged in the report's reason text.
    two_digit_year_pivot: Optional[int] = 69
    # 5. "Submitted" counts as received?  (default: no)
    submitted_is_received: bool = False
    # 6. "Received in revised form" counts as received? (default: no)
    received_in_revised_form_counts: bool = False
    # 8. Range rules
    min_year: int = 1990
    allow_future_dates: bool = False
    # 9. File types
    supported_extensions: Tuple[str, ...] = (".docx",)
    # Tracked changes: text inside a tracked DELETION is ignored by default.
    include_deleted_text: bool = False
    # 7. Incomplete dates (month+year, year only, day+month) are always
    #    reported as INVALID_DATE; nothing is guessed.


DEFAULT_POLICY = Policy()
