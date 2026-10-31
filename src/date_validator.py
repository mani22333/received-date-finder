"""Turn a RawDate into a real calendar date (or a clear problem)."""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .config import AMBIGUOUS, INVALID_DATE, SUCCESS, Policy
from .date_patterns import MONTHS, RawDate


@dataclass
class Outcome:
    status: str
    date: Optional[date] = None
    readings: List[date] = field(default_factory=list)   # for AMBIGUOUS
    warnings: List[str] = field(default_factory=list)
    reason: str = ""


def _build(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _expand_year(ys: str, policy: Policy):
    """Return (year, warning). year None means 'cannot decide'."""
    if len(ys) == 4:
        return int(ys), None
    if policy.two_digit_year_pivot is None:
        return None, None
    yy = int(ys)
    year = 2000 + yy if yy <= policy.two_digit_year_pivot else 1900 + yy
    return year, (f"two-digit year '{ys}' read as {year} (pivot {policy.two_digit_year_pivot}; "
                  f"rule not yet confirmed by product owner)")


def range_problem(d: date, policy: Policy, today: date) -> Optional[str]:
    if d.year < policy.min_year:
        return f"{d.isoformat()} is before the accepted minimum year {policy.min_year}"
    if not policy.allow_future_dates and d > today:
        return f"{d.isoformat()} is in the future (today is {today.isoformat()})"
    return None


def _finish(d: date, warnings: List[str], policy: Policy, today: date) -> Outcome:
    problem = range_problem(d, policy, today)
    if problem:
        return Outcome(INVALID_DATE, None, [], warnings, problem)
    return Outcome(SUCCESS, d, [], warnings, "")


def interpret(raw: RawDate, policy: Policy, today: date) -> Outcome:
    g, text = raw.groups, raw.text
    if raw.kind in ("month_year", "day_month", "year_only"):
        return Outcome(INVALID_DATE, reason=f"'{text}' is an incomplete date (day, month and year are all needed)")

    warnings: List[str] = []
    if raw.kind in ("iso", "compact"):
        d = _build(int(g["y"]), int(g["m"]), int(g["d"]))
        if d is None:
            return Outcome(INVALID_DATE, reason=f"'{text}' is not a real calendar date")
        return _finish(d, warnings, policy, today)

    year, warn = _expand_year(g["y"], policy)
    if year is None:
        return Outcome(AMBIGUOUS, reason=f"'{text}' has a two-digit year and the year rule is not confirmed")
    if warn:
        warnings.append(warn)

    if raw.kind in ("dmy_name", "mdy_name"):
        d = _build(year, MONTHS[g["mon"].lower()], int(g["d"]))
        if d is None:
            return Outcome(INVALID_DATE, reason=f"'{text}' is not a real calendar date")
        return _finish(d, warnings, policy, today)

    # numeric: a/b/yyyy -> day-first or month-first
    a, b = int(g["a"]), int(g["b"])
    readings: List[date] = []
    for cand in (_build(year, b, a), _build(year, a, b)):  # day-first, month-first
        if cand and cand not in readings:
            readings.append(cand)
    if not readings:
        return Outcome(INVALID_DATE, reason=f"'{text}' is not a real calendar date in day-first or month-first order")
    if len(readings) == 1:
        warnings.append(f"'{text}': only one reading is a real date ({readings[0].isoformat()})")
        return _finish(readings[0], warnings, policy, today)

    # two different valid readings
    mode = policy.ambiguous_numeric
    if mode == "day_first":
        return _finish(readings[0], warnings + [f"'{text}' read day-first by policy"], policy, today)
    if mode == "month_first":
        return _finish(readings[1], warnings + [f"'{text}' read month-first by policy"], policy, today)
    return Outcome(AMBIGUOUS, None, readings, warnings,
                   f"'{text}' could be {readings[0].isoformat()} (day-first) or "
                   f"{readings[1].isoformat()} (month-first)")
