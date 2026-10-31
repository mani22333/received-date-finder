#!/usr/bin/env python3
"""Received Date Finder.

  python main.py path/to/manuscript.docx   -> prints YYYY-MM-DD (or a status word)
  python main.py input/                    -> every .docx in the folder + CSV report
  python main.py --write-test-report       -> run all scenarios, write test_report.csv
"""
import argparse
import sys
from pathlib import Path

from src.config import DEFAULT_POLICY, EXIT_CODES, SUCCESS
from src.date_extractor import ExtractionResult, extract_received_date
from src.report_generator import write_extraction_report, write_test_report


def process_folder(folder: Path):
    results = []
    for p in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
        if p.is_file() and (p.suffix.lower() in DEFAULT_POLICY.supported_extensions or p.name.startswith("~$")):
            results.append(extract_received_date(p))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find the received date in manuscript Word files.")
    ap.add_argument("path", nargs="?", help="a .docx file or a folder of .docx files")
    ap.add_argument("--output-dir", default="output", help="where CSV reports go (default: output)")
    ap.add_argument("--write-test-report", action="store_true",
                    help="run every scenario and write test_report.csv (exit 1 if any FAIL)")
    args = ap.parse_args(argv)
    out_dir = Path(args.output_dir)

    if args.write_test_report:
        from tests.scenario_runner import run_all  # imported lazily: tests are not needed for normal use
        rows = run_all(sample_dir=Path(args.path) if args.path else Path("input"))
        write_test_report(rows, out_dir / "test_report.csv")
        failed = [r for r in rows if r["status"] != "PASS"]
        print(f"{len(rows) - len(failed)}/{len(rows)} scenarios PASS -> {out_dir / 'test_report.csv'}")
        for r in failed:
            print(f"FAIL {r['test_id']}: expected {r['expected_result']} got {r['actual_result']} {r['error_message']}")
        return 1 if failed else 0

    if not args.path:
        ap.print_usage(sys.stderr)
        return 2
    target = Path(args.path)
    if target.is_dir():
        results = process_folder(target)
        write_extraction_report(results, out_dir / "extraction_report.csv")
        for r in results:
            print(f"{r.filename}\t{r.status}\t{r.date}")
        print(f"{len(results)} file(s) processed -> {out_dir / 'extraction_report.csv'}", file=sys.stderr)
        return 0

    r: ExtractionResult = extract_received_date(target)
    if r.status == SUCCESS:
        print(r.date)
    else:
        print(r.status)
        print(f"{r.status}: {r.reason}", file=sys.stderr)
    return EXIT_CODES[r.status]


if __name__ == "__main__":
    sys.exit(main())
