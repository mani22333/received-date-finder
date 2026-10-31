"""Samples from input/ and the command line."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.config import DEFAULT_POLICY
from src.date_extractor import extract_received_date
from tests.scenarios import SAMPLES, TODAY
from tests.scenario_runner import _fmt

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "input"


def cli(*args):
    return subprocess.run([sys.executable, str(ROOT / "main.py"), *map(str, args)],
                          capture_output=True, text=True, cwd=ROOT)


@unittest.skipUnless((INPUT / "merged_01.docx").exists(), "sample manuscripts not in input/")
class SampleTests(unittest.TestCase):
    def test_every_sample(self):
        for n, expected in SAMPLES.items():
            with self.subTest(sample=n):
                r = extract_received_date(INPUT / f"merged_{n:02d}.docx", DEFAULT_POLICY, TODAY)
                self.assertEqual(_fmt(r.status, r.date), _fmt(*expected), r.reason)

    def test_samples_are_not_modified(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUT.glob("*.docx")}
        for p in INPUT.glob("*.docx"):
            extract_received_date(p, DEFAULT_POLICY, TODAY)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUT.glob("*.docx")}
        self.assertEqual(before, after)

    def test_folder_report_has_a_row_per_file(self):
        with tempfile.TemporaryDirectory() as out:
            res = cli(INPUT, "--output-dir", out)
            self.assertEqual(res.returncode, 0, res.stderr)
            lines = (Path(out) / "extraction_report.csv").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines) - 1, len(list(INPUT.glob("*.docx"))))
            self.assertEqual(lines[0], "filename,extracted_date,status,original_date_text,location,reason")
            simple = (Path(out) / "received_dates.csv").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(simple[0], "filename,received_date")
            self.assertEqual(simple[1], "merged_01.docx,2026-01-02")
            self.assertEqual(len(simple), len(lines))


class CommandLineTests(unittest.TestCase):
    def test_output_is_exactly_the_date(self):
        from tests.docx_factory import make_docx
        with tempfile.TemporaryDirectory() as d:
            p = make_docx(Path(d) / "a.docx", {"body": ["Received: 2 March 2024"]})
            res = cli(p)
            self.assertEqual((res.returncode, res.stdout), (0, "2024-03-02\n"))   # zero-padded, nothing else

    def test_exit_codes(self):
        from tests.docx_factory import make_docx
        with tempfile.TemporaryDirectory() as d:
            nf = make_docx(Path(d) / "n.docx", {"body": ["Accepted: 2 March 2024"]})
            self.assertEqual((cli(nf).returncode, cli(nf).stdout.strip()), (1, "NOT_FOUND"))
            self.assertIn("accepted", cli(nf).stderr)
            self.assertEqual(cli(Path(d) / "missing.docx").returncode, 2)
            self.assertEqual(cli().returncode, 2)


if __name__ == "__main__":
    unittest.main()
