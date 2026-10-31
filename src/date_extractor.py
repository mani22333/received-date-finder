"""Find the received date using the label that sits in front of it."""
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Optional

from .config import (AMBIGUOUS, DEFAULT_POLICY, FILE_ERROR, INVALID_DATE, MULTIPLE_DATES,
                     NOT_FOUND, SUCCESS, Policy)
from .date_patterns import (OTHER_LABEL_RE, RawDate, label_boundary_ok, match_date_at,
                            received_label_regex)
from .date_validator import Outcome, interpret
from .document_reader import Block, DocumentReadError, read_document

_AFTER_LABEL = re.compile(r"[\s:\-=.]*(?:on\b[\s:\-=.]*)?", re.I)


@dataclass
class Hit:
    """One thing found in one paragraph."""
    kind: str                  # date | label_only | garbage
    label: str
    raw: Optional[RawDate] = None
    garbage: str = ""


@dataclass
class Candidate:
    label: str
    date_text: str
    location: str
    outcome: Outcome


@dataclass
class ExtractionResult:
    filename: str
    status: str
    date: str = ""
    original_date_text: str = ""
    location: str = ""
    reason: str = ""
    warnings: List[str] = field(default_factory=list)
    candidates: List[Candidate] = field(default_factory=list)


def scan_text(text: str, policy: Policy = DEFAULT_POLICY) -> List[Hit]:
    """Find received labels in one paragraph and what follows each."""
    regex = received_label_regex(policy.submitted_is_received, policy.received_in_revised_form_counts)
    hits: List[Hit] = []
    for m in regex.finditer(text):
        if not label_boundary_ok(text, m.start()):
            continue
        rest_start = _AFTER_LABEL.match(text, m.end()).end()
        raw = match_date_at(text, rest_start)
        if raw:
            hits.append(Hit("date", m.group(0), raw))
            continue
        rest = text[rest_start:]
        if not rest.strip():
            hits.append(Hit("label_only", m.group(0)))
            continue
        explicit = bool(re.match(r"\s*[:\-=]", text[m.end():]))
        segment = re.split(r"[;|]", rest, maxsplit=1)[0].strip()
        if explicit and 0 < len(segment.split()) <= 3:
            hits.append(Hit("garbage", m.group(0), garbage=segment))
    return hits


def _other_dates(blocks: List[Block], policy: Policy, today: date) -> List[date]:
    """Clear (non-ambiguous) revised/accepted/published dates, for chronology."""
    found = []
    for b in blocks:
        if b.is_reference_entry:
            continue
        for m in OTHER_LABEL_RE.finditer(b.text):
            if not label_boundary_ok(b.text, m.start()):
                continue
            raw = match_date_at(b.text, _AFTER_LABEL.match(b.text, m.end()).end())
            if raw:
                out = interpret(raw, policy, today)
                if out.status == SUCCESS:
                    found.append(out.date)
    return found


def _other_labels_present(blocks: List[Block]) -> List[str]:
    names = set()
    for b in blocks:
        if not b.is_reference_entry:
            for m in OTHER_LABEL_RE.finditer(b.text):
                names.add(m.group("label").lower())
    return sorted(names)


def _collect(blocks: List[Block], policy: Policy, today: date) -> List[Candidate]:
    cands: List[Candidate] = []
    for i, b in enumerate(blocks):
        if b.is_reference_entry or not b.text:
            continue
        for hit in scan_text(b.text, policy):
            if hit.kind == "date":
                cands.append(Candidate(hit.label, hit.raw.text, b.location, interpret(hit.raw, policy, today)))
            elif hit.kind == "garbage":
                cands.append(Candidate(hit.label, hit.garbage, b.location, Outcome(
                    INVALID_DATE, reason=f"label '{hit.label}' is followed by '{hit.garbage}', which is not a date")))
            else:  # label alone: the date may be in the next paragraph / table cell
                nxt = next((x for x in blocks[i + 1:i + 4] if x.text and x.part == b.part), None)
                raw = match_date_at(nxt.text, 0) if nxt else None
                if raw:
                    cands.append(Candidate(hit.label, raw.text, f"{b.location} -> {nxt.location}",
                                           interpret(raw, policy, today)))
    return cands


def _key(c: Candidate):
    o = c.outcome
    if o.status == SUCCESS:
        return ("ok", o.date)
    if o.status == AMBIGUOUS:
        return ("amb", c.date_text.lower())
    return ("bad", c.date_text.lower())


def analyse_blocks(blocks: List[Block], filename: str, policy: Policy = DEFAULT_POLICY,
                   today: Optional[date] = None) -> ExtractionResult:
    today = today or date.today()
    cands = _collect(blocks, policy, today)
    if not cands:
        others = _other_labels_present(blocks)
        why = "no received-date label with a date was found"
        if others:
            why += f" (only other labelled dates present: {', '.join(others)})"
        return ExtractionResult(filename, NOT_FOUND, reason=why)

    distinct, seen = [], set()
    for c in cands:
        if _key(c) not in seen:
            seen.add(_key(c))
            distinct.append(c)

    if len(distinct) > 1:
        valid = [c for c in distinct if c.outcome.status == SUCCESS]
        if policy.multiple_received in ("first", "latest") and len(valid) == len(distinct):
            chosen = distinct[0] if policy.multiple_received == "first" else max(valid, key=lambda c: c.outcome.date)
            return _success(filename, chosen, cands,
                            extra=[f"{len(distinct)} different received dates; '{policy.multiple_received}' rule applied"])
        listing = "; ".join(f"{c.date_text} [{c.outcome.status}] at {c.location}" for c in distinct)
        return ExtractionResult(filename, MULTIPLE_DATES, original_date_text=" | ".join(c.date_text for c in distinct),
                                location=" | ".join(c.location for c in distinct),
                                reason=f"{len(distinct)} different received entries: {listing}", candidates=cands)

    c = distinct[0]
    o = c.outcome
    if o.status == SUCCESS:
        return _success(filename, c, cands)
    if o.status == AMBIGUOUS and o.readings and policy.ambiguous_numeric == "chronology":
        others = _other_dates(blocks, policy, today)
        ok = [r for r in o.readings if others and all(r <= x for x in others)]
        if len(ok) == 1:
            c.outcome = Outcome(SUCCESS, ok[0], [], o.warnings + [
                f"'{c.date_text}' resolved by chronology: only {ok[0].isoformat()} is not later than the "
                f"revised/accepted/published dates"], "")
            return _success(filename, c, cands)
    hint = ""
    if o.status == AMBIGUOUS and o.readings:
        others = _other_dates(blocks, policy, today)
        ok = [r for r in o.readings if others and all(r <= x for x in others)]
        if len(ok) == 1:
            hint = f" (hint only, not applied: {ok[0].isoformat()} is the only reading consistent with the other dates)"
    return ExtractionResult(filename, o.status, original_date_text=c.date_text, location=c.location,
                            reason=o.reason + hint, warnings=o.warnings, candidates=cands)


def _success(filename, c: Candidate, cands, extra=None) -> ExtractionResult:
    warnings = list(c.outcome.warnings) + (extra or [])
    reason = f"found after label '{c.label}'" + (f"; note: {'; '.join(warnings)}" if warnings else "")
    return ExtractionResult(filename, SUCCESS, c.outcome.date.isoformat(), c.date_text, c.location,
                            reason, warnings, cands)


def extract_received_date(path, policy: Policy = DEFAULT_POLICY, today: Optional[date] = None) -> ExtractionResult:
    """Never raises: every problem becomes a status."""
    path = Path(path)
    try:
        blocks = read_document(path, policy)
    except DocumentReadError as exc:
        return ExtractionResult(path.name, FILE_ERROR, reason=str(exc))
    except Exception as exc:  # last safety net
        return ExtractionResult(path.name, FILE_ERROR, reason=f"unexpected error ({type(exc).__name__}: {exc})")
    try:
        return analyse_blocks(blocks, path.name, policy, today)
    except Exception as exc:
        return ExtractionResult(path.name, FILE_ERROR, reason=f"unexpected error ({type(exc).__name__}: {exc})")
