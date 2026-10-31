import io
import unittest
from pathlib import Path

try:
    from app import app
except ImportError:  # Flask not installed
    app = None

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "input"


@unittest.skipIf(app is None, "Flask not installed")
class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def upload(self, names):
        data = {"files": [(io.BytesIO((INPUT / n).read_bytes()), n) for n in names]}
        return self.client.post("/", data=data, content_type="multipart/form-data")

    def test_page_loads(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"multiple", r.data)

    @unittest.skipUnless((INPUT / "merged_01.docx").exists(), "samples missing")
    def test_multiple_files_in_one_upload(self):
        r = self.upload(["merged_01.docx", "merged_05.docx", "merged_08.docx", "merged_12.docx", "merged_19.docx"])
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("2026-01-02", html)
        for status in ("SUCCESS", "AMBIGUOUS", "NOT_FOUND", "FILE_ERROR", "INVALID_DATE"):
            self.assertIn(status, html)
        for name in ("merged_01.docx", "merged_05.docx", "merged_08.docx", "merged_12.docx", "merged_19.docx"):
            self.assertIn(name, html)

    def test_bad_upload_does_not_crash(self):
        r = self.client.post("/", data={"files": [(io.BytesIO(b"junk"), "x.docx"), (io.BytesIO(b"hi"), "y.txt")]},
                             content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_data(as_text=True).count('class="s FILE_ERROR"'), 2)   # one badge per bad file

    def test_csv_download(self):
        r = self.client.post("/download", data={"data": '[{"filename":"a.docx","date":"2026-01-02","status":"SUCCESS"}]'})
        self.assertEqual(r.mimetype, "text/csv")
        self.assertEqual(r.get_data(as_text=True).splitlines(), ["filename,received_date,status", "a.docx,2026-01-02,SUCCESS"])
        self.assertEqual(self.client.post("/download", data={"data": "not json"}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
