"""Run every scenario for real and return rows for test_report.csv."""
import shutil
import tempfile
from pathlib import Path

from src.config import DEFAULT_POLICY
from src.date_extractor import extract_received_date

from .docx_factory import make_docx
from .scenarios import SAMPLE_NOTES, SAMPLES, SCENARIOS, TODAY


def build_input(scn, workdir: Path) -> Path:
    if scn.raw is not None:
        name, data = scn.raw
        p = workdir / name
        if data == "DIR":
            p.mkdir()
        elif data is not None:
            p.write_bytes(data)
        return p
    return make_docx(workdir / f"{scn.id}.docx", scn.spec)


def _fmt(status, date):
    return f"{status} {date}".strip()


def run_scenario(scn, workdir: Path):
    path = build_input(scn, workdir)
    res = extract_received_date(path, scn.policy or DEFAULT_POLICY, today=TODAY)
    return path, res


def run_all(sample_dir: Path = Path("input")):
    rows = []
    work = Path(tempfile.mkdtemp(prefix="scn_"))
    try:
        for scn in SCENARIOS:
            sub = work / scn.id
            sub.mkdir()
            exp = _fmt(*scn.expected)
            try:
                path, res = run_scenario(scn, sub)
                act = _fmt(res.status, res.date)
                ok = act == exp
                err = "" if ok else f"{res.reason}"
                fname = path.name
            except Exception as exc:  # a crash is a failed scenario, not a failed report
                act, ok, err, fname = "CRASH", False, f"{type(exc).__name__}: {exc}", ""
            rows.append({"test_id": scn.id, "filename": fname, "scenario": f"[{scn.group}] {scn.desc}",
                         "expected_result": exp, "actual_result": act, "status": "PASS" if ok else "FAIL",
                         "error_message": err})
        for n, expected in sorted(SAMPLES.items()):
            f = sample_dir / f"merged_{n:02d}.docx"
            exp = _fmt(*expected)
            if not f.exists():
                rows.append({"test_id": f"SAMPLE-{n:02d}", "filename": f.name, "scenario": f"[sample] {SAMPLE_NOTES[n]}",
                             "expected_result": exp, "actual_result": "MISSING", "status": "FAIL",
                             "error_message": f"sample file not found in {sample_dir}"})
                continue
            res = extract_received_date(f, DEFAULT_POLICY, today=TODAY)
            act = _fmt(res.status, res.date)
            rows.append({"test_id": f"SAMPLE-{n:02d}", "filename": f.name, "scenario": f"[sample] {SAMPLE_NOTES[n]}",
                         "expected_result": exp, "actual_result": act, "status": "PASS" if act == exp else "FAIL",
                         "error_message": "" if act == exp else res.reason})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return rows
