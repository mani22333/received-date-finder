#!/usr/bin/env bash
# Set up, test, process the manuscripts, write the CSV reports.
# Exits non-zero if any automated test or scenario fails.
set -euo pipefail
cd "$(dirname "$0")"

PY=python3
if [ ! -d .venv ]; then
  if $PY -m venv --system-site-packages .venv 2>/dev/null; then :; else echo "note: venv not available, using system python"; fi
fi
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PY=python
fi

echo "== 1. Installing dependencies"
if ! $PY -m pip install -q -r requirements.txt; then
  echo "note: pip install failed (offline?). Continuing with already-installed packages."
fi
$PY -c "import docx, lxml" || { echo "ERROR: python-docx and lxml are required"; exit 1; }

echo "== 2. Running automated tests"
if $PY -c "import pytest" 2>/dev/null; then
  $PY -m pytest -q tests
else
  echo "note: pytest not installed, using unittest (same tests)"
  $PY -m unittest discover -s tests -t . 
fi

echo "== 3. Processing manuscripts in input/"
mkdir -p output
$PY main.py input --output-dir output

echo "== 4. Running all scenarios -> output/test_report.csv"
$PY main.py --write-test-report --output-dir output

cp output/test_report.csv test_report.csv   # the submission asks for test_report.csv at the repo root
echo "== Done. Reports: output/extraction_report.csv, output/test_report.csv (copy: ./test_report.csv)"
