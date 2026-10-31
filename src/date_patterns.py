"""Date formats and received-label patterns (pure regex, no document access)."""
import re
from dataclasses import dataclass
from typing import Dict, Optional

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_MONTH = "|".join(sorted(MONTHS, key=len, reverse=True))
_WEEKDAY = (r"(?:monday|mon|tuesday|tues|tue|wednesday|wed|thursday|thurs|thur|thu|"
            r"friday|fri|saturday|sat|sunday|sun)")

_SPACES = re.compile(r"[\u00a0\u2000-\u200a\u202f\u205f\u3000\t\r\n\x0b\x0c]")
_INVISIBLE = re.compile(r"[\u200b-\u200d\u2060\ufeff\u00ad]")
_DASHES = re.compile(r"[\u2010-\u2015\u2212\ufe58\ufe63\uff0d]")


def normalize_text(text: str) -> str:
    """Make odd spaces, dashes and quotes plain so patterns stay simple."""
    text = _INVISIBLE.sub("", text)
    text = _SPACES.sub(" ", text)
    text = _DASHES.sub("-", text)
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'")
    return re.sub(r" {2,}", " ", text).strip()


@dataclass
class RawDate:
    """A date-looking piece of text, not yet checked against the calendar."""
    kind: str                 # iso | compact | dmy_name | mdy_name | numeric | month_year | day_month | year_only
    groups: Dict[str, str]
    text: str                 # the exact matched text
    end: int                  # end offset in the searched string


_FLAGS = re.I
_PATTERNS = [
    ("iso", re.compile(r"(?P<y>\d{4})(?P<s>[-/.])(?P<m>\d{1,2})(?P=s)(?P<d>\d{1,2})(?!\d)")),
    ("compact", re.compile(r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})(?!\d)")),
    ("dmy_name", re.compile(
        rf"(?P<d>\d{{1,2}})(?:st|nd|rd|th)?(?:\s+of\s+|[\s\-./,]*)(?P<mon>{_MONTH})(?![a-z])"
        rf"\.?[\s,\-./]*(?P<y>\d{{4}}|\d{{2}})(?!\d)", _FLAGS)),
    ("mdy_name", re.compile(
        rf"(?P<mon>{_MONTH})(?![a-z])\.?[\s\-./]*(?P<d>\d{{1,2}})(?:st|nd|rd|th)?(?!\d)"
        rf"[\s,\-./]+(?P<y>\d{{4}}|\d{{2}})(?!\d)", _FLAGS)),
    ("numeric", re.compile(
        r"(?P<a>\d{1,2})(?P<s>[/.\-])(?P<b>\d{1,2})(?P=s)(?P<y>\d{4}|\d{2})(?!\d)")),
    ("month_year", re.compile(rf"(?P<mon>{_MONTH})(?![a-z])\.?[\s,\-./]*(?P<y>\d{{4}})(?!\d)", _FLAGS)),
    ("day_month", re.compile(rf"(?P<d>\d{{1,2}})(?:st|nd|rd|th)?(?:\s+of\s+|\s+)(?P<mon>{_MONTH})(?![a-z])", _FLAGS)),
    ("year_only", re.compile(r"(?P<y>(?:19|20)\d{2})(?!\d)")),
]
_LEAD = re.compile(rf"[\s,]*(?:{_WEEKDAY}\.?,?\s*)?", re.I)


def match_date_at(text: str, start: int = 0) -> Optional[RawDate]:
    """Match a date that begins right at `start` (after spaces/weekday)."""
    lead = _LEAD.match(text, start)
    pos = lead.end() if lead else start
    for kind, pat in _PATTERNS:
        m = pat.match(text, pos)
        if m:
            return RawDate(kind, m.groupdict(), m.group(0), m.end())
    return None


# ---- labels ---------------------------------------------------------------

_cache: Dict[tuple, "re.Pattern"] = {}


def received_label_regex(submitted_counts: bool = False, revised_form_counts: bool = False):
    """Regex for 'received' labels. 'Received in revised form' is excluded
    unless the policy says otherwise."""
    key = (submitted_counts, revised_form_counts)
    if key in _cache:
        return _cache[key]
    word = r"(?:received|recvd|recd|rec'd|rcvd)"
    core = rf"(?:(?:date|manuscript|article|paper)\s+)*{word}"
    if revised_form_counts:   # policy says: 'received in revised form' is a received label too
        core += r"(?:\s*\(?\s*(?:in\s+|after\s+)?(?:revised|revision|amended)(?:\s+form)?\s*\)?)?"
    else:
        core += r"(?!\s*\(?\s*(?:in\s+|after\s+)?(?:revis|amend))"
    core += r"(?:\s+on\b|\s+date\b)?"
    alts = [core, r"(?:date\s+of\s+receipt|receipt\s+date)"]
    if submitted_counts:
        alts.append(r"(?<![a-z\-])submitted(?:\s+on\b)?")
    _cache[key] = re.compile(r"(?<![a-z])(?:" + "|".join(alts) + r")(?![a-z])", re.I)
    return _cache[key]


# Labels of OTHER dates; used for reasons and the optional chronology rule.
OTHER_LABEL_RE = re.compile(
    r"(?<![a-z])(?P<label>re-?submitted|submitted|revised|accepted|published(?:\s+online)?|"
    r"available\s+online|online|issue\s+date)(?![a-z])", re.I)

BOUNDARY_WORDS = re.compile(r"(?:history|dates?|timeline|information|details)\s*$", re.I)
BOUNDARY_CHARS = ";|,([:.\u2022\u00b7-"


def label_boundary_ok(text: str, start: int) -> bool:
    """A real label starts the line or follows a separator (not mid-sentence:
    'We received funding...' must not count)."""
    prefix = text[:start].rstrip()
    if not prefix:
        return True
    return prefix[-1] in BOUNDARY_CHARS or bool(BOUNDARY_WORDS.search(prefix))
