"""Small website: upload one or many .docx manuscripts, get the received date for each.

    python app.py     ->  open http://127.0.0.1:5000

Uses the same extractor as main.py, so results are identical.
"""
import csv
import io
import json
import tempfile
from pathlib import Path

from flask import Flask, Response, render_template_string, request

from src.date_extractor import extract_received_date

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB per upload

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Received Date Finder</title>
<style>
 body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#1f2933}
 h1{font-size:1.5rem;margin-bottom:.2rem} p.sub{color:#52606d;margin-top:0}
 .box{border:2px dashed #9aa5b1;border-radius:10px;padding:1.5rem;text-align:center;background:#f8fafc}
 button{background:#2563eb;color:#fff;border:0;border-radius:8px;padding:.6rem 1.2rem;font-size:1rem;cursor:pointer}
 button.alt{background:#fff;color:#2563eb;border:1px solid #2563eb}
 table{border-collapse:collapse;width:100%;margin-top:1.2rem} th,td{border-bottom:1px solid #e4e7eb;padding:.5rem;text-align:left;vertical-align:top}
 th{background:#f0f4f8} .date{font-weight:600;font-variant-numeric:tabular-nums}
 .s{font-size:.8rem;padding:.1rem .5rem;border-radius:99px;white-space:nowrap}
 .SUCCESS{background:#d1fae5;color:#065f46} .NOT_FOUND,.AMBIGUOUS,.MULTIPLE_DATES{background:#fef3c7;color:#92400e}
 .INVALID_DATE,.FILE_ERROR{background:#fee2e2;color:#991b1b} .why{color:#52606d;font-size:.85rem}
</style></head><body>
<h1>Received Date Finder</h1>
<p class="sub">Upload one or more Word (.docx) manuscripts. You get the received date as YYYY-MM-DD.</p>
<form method="post" enctype="multipart/form-data" class="box">
  <input type="file" name="files" accept=".docx" multiple required>
  <p><button type="submit">Find received dates</button></p>
</form>
{% if rows %}
<table>
 <tr><th>File</th><th>Received date</th><th>Status</th><th>Details</th></tr>
 {% for r in rows %}
 <tr><td>{{ r.filename }}</td><td class="date">{{ r.date }}</td>
     <td><span class="s {{ r.status }}">{{ r.status }}</span></td>
     <td class="why">{% if r.original %}Found as "{{ r.original }}"{% if r.location %} in {{ r.location }}{% endif %}.{% endif %} {{ r.reason }}</td></tr>
 {% endfor %}
</table>
<form method="post" action="/download" style="margin-top:1rem">
  <input type="hidden" name="data" value="{{ data }}">
  <button class="alt" type="submit">Download results (CSV)</button>
</form>
{% endif %}
</body></html>"""


def _process(storage_files):
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(storage_files):
            original = Path(f.filename or "").name or f"file_{i}"
            folder = Path(tmp) / str(i)
            folder.mkdir()
            path = folder / original            # same name, own folder: no clashes, no path tricks
            f.save(path)
            r = extract_received_date(path)
            rows.append({"filename": original, "date": r.date, "status": r.status,
                         "original": r.original_date_text, "location": r.location, "reason": r.reason})
    return rows


@app.route("/", methods=["GET", "POST"])
def index():
    rows = []
    if request.method == "POST":
        files = [f for f in request.files.getlist("files") if f and f.filename]
        rows = _process(files)
    return render_template_string(PAGE, rows=rows, data=json.dumps(rows))


@app.post("/download")
def download():
    try:
        rows = json.loads(request.form.get("data", "[]"))
    except ValueError:
        rows = []
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["filename", "received_date", "status"])
    for r in rows:
        w.writerow([r.get("filename", ""), r.get("date", ""), r.get("status", "")])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=received_dates.csv"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
