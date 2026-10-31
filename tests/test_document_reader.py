import tempfile
import unittest
from pathlib import Path

import docx

from src.document_reader import DocumentReadError, read_document
from tests.docx_factory import make_docx


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def blocks(self, spec, policy=None):
        p = make_docx(self.dir / "t.docx", spec)
        return read_document(p) if policy is None else read_document(p, policy)

    def texts(self, blocks):
        return [(b.kind, b.text) for b in blocks if b.text]

    def test_fixture_is_a_valid_docx(self):
        p = make_docx(self.dir / "v.docx", {"body": ["hello"], "header": ["h"], "footer": ["f"]})
        self.assertEqual(docx.Document(str(p)).paragraphs[0].text, "hello")

    def test_all_parts_are_read_in_order(self):
        b = self.blocks({"body": ["B1"], "header": ["H1"], "footer": ["F1"], "footnotes": ["N1"],
                         "endnotes": ["E1"], "comments": ["C1"]})
        self.assertEqual(self.texts(b), [("body", "B1"), ("header", "H1"), ("footer", "F1"),
                                         ("footnote", "N1"), ("endnote", "E1"), ("comment", "C1")])

    def test_table_and_nested_table(self):
        b = self.blocks({"body": [("table", [["a", ("table", [["inner"]])]])]})
        inner = [x for x in b if x.text == "inner"][0]
        self.assertTrue(inner.in_table)
        self.assertIn("table", inner.location)

    def test_textbox_read_once_not_twice(self):
        b = self.blocks({"body": [("textbox", "boxed")]})
        self.assertEqual([x.text for x in b if x.text == "boxed"], ["boxed"])   # Fallback copy is skipped
        self.assertTrue([x for x in b if x.text == "boxed"][0].in_textbox)

    def test_split_runs_are_joined(self):
        b = self.blocks({"body": [("runs", ["Rece", "ived: 1 Ma", "r 2024"])]})
        self.assertEqual(b[0].text, "Received: 1 Mar 2024")

    def test_tracked_changes(self):
        self.assertEqual(self.texts(self.blocks({"body": [("ins", "added")]})), [("body", "added")])
        self.assertEqual(self.texts(self.blocks({"body": [("del", "removed")]})), [])

    def test_reference_entries_flagged(self):
        b = self.blocks({"body": ["References", "[1] Smith 2019", "Received: 1 Jan 2024"]})
        self.assertEqual([x.is_reference_entry for x in b], [False, True, False])

    def test_errors_have_clear_messages(self):
        bad = self.dir / "bad.docx"
        bad.write_bytes(b"not a zip")
        with self.assertRaisesRegex(DocumentReadError, "corrupt"):
            read_document(bad)
        with self.assertRaisesRegex(DocumentReadError, "not found"):
            read_document(self.dir / "nope.docx")
        pdf = self.dir / "x.pdf"
        pdf.write_bytes(b"%PDF")
        with self.assertRaisesRegex(DocumentReadError, "unsupported"):
            read_document(pdf)


if __name__ == "__main__":
    unittest.main()
