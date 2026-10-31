"""Read every text-bearing part of a .docx in document order.

python-docx opens/validates the package and walks its parts. The text itself
is read from the raw XML (lxml) because python-docx cannot reach text boxes,
footnotes, endnotes, comments, or tracked changes, and loses their order.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Tuple

import docx
from lxml import etree

from .config import DEFAULT_POLICY, Policy
from .date_patterns import normalize_text

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def _q(tag: str) -> str:
    return f"{{{W}}}{tag}"


FALLBACK = f"{{{MC}}}Fallback"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_PART_KINDS = [
    (re.compile(r"^/word/document\.xml$"), "body", 0),
    (re.compile(r"^/word/header\d*\.xml$"), "header", 1),
    (re.compile(r"^/word/footer\d*\.xml$"), "footer", 2),
    (re.compile(r"^/word/footnotes\.xml$"), "footnote", 3),
    (re.compile(r"^/word/endnotes\.xml$"), "endnote", 4),
    (re.compile(r"^/word/comments\w*\.xml$"), "comment", 5),
]
_REF_HEADINGS = {"references", "reference list", "bibliography", "works cited", "literature cited"}
_REF_ENTRY = re.compile(r"\s*(?:\[\d+\]|\(\d+\))\s")
_REF_ENTRY_NUM = re.compile(r"\s*\d+[.)]\s")


class DocumentReadError(Exception):
    """The file cannot be read as a Word document."""


@dataclass
class Block:
    text: str                 # normalised text of one paragraph
    part: str                 # e.g. word/header1.xml
    kind: str                 # body | header | footer | footnote | endnote | comment
    index: int                # 1-based paragraph number inside the part
    in_table: bool = False
    in_textbox: bool = False
    is_reference_entry: bool = False

    @property
    def location(self) -> str:
        parts = [self.kind]
        if self.in_table:
            parts.append("table")
        if self.in_textbox:
            parts.append("textbox")
        return f"{'/'.join(parts)} (paragraph {self.index})"


# ---- XML walking ------------------------------------------------------------

def _textboxes_in(p) -> list:
    found = []

    def walk(e):
        for c in e:
            if not isinstance(c.tag, str) or c.tag == FALLBACK:
                continue
            if c.tag == _q("txbxContent"):
                found.append(c)
                continue
            walk(c)
    walk(p)
    return found


def _iter_paragraphs(el, in_table=False, in_textbox=False) -> Iterator[Tuple[object, bool, bool]]:
    for child in el:
        tag = child.tag
        if not isinstance(tag, str) or tag == FALLBACK:
            continue
        if tag == _q("p"):
            yield child, in_table, in_textbox
            for box in _textboxes_in(child):
                yield from _iter_paragraphs(box, in_table, True)
        elif tag == _q("tbl"):
            yield from _iter_paragraphs(child, True, in_textbox)
        elif tag in (_q("del"), _q("moveFrom")):
            continue
        else:
            yield from _iter_paragraphs(child, in_table, in_textbox)


def _paragraph_text(p, include_deleted: bool) -> str:
    out: List[str] = []

    def walk(e):
        for c in e:
            t = c.tag
            if not isinstance(t, str):
                continue
            if t == _q("t"):
                out.append(c.text or "")
            elif t == _q("delText"):
                if include_deleted:
                    out.append(c.text or "")
            elif t in (_q("tab"), _q("br"), _q("cr")):
                out.append(" ")
            elif t == _q("noBreakHyphen"):
                out.append("-")
            elif t in (_q("txbxContent"), FALLBACK, _q("instrText"), _q("pPr"), _q("rPr")):
                continue
            elif t in (_q("del"), _q("moveFrom")) and not include_deleted:
                continue
            else:
                walk(c)
    walk(p)
    return "".join(out)


# ---- public API -------------------------------------------------------------

def check_file(path: Path, policy: Policy = DEFAULT_POLICY) -> None:
    """Raise DocumentReadError with a clear reason for unusable input."""
    if not path.exists():
        raise DocumentReadError(f"file not found: {path}")
    if path.is_dir():
        raise DocumentReadError(f"path is a folder, not a file: {path}")
    if path.name.startswith("~$"):
        raise DocumentReadError("temporary Word lock file (~$...), not a real document")
    if path.suffix.lower() not in policy.supported_extensions:
        raise DocumentReadError(
            f"unsupported file type '{path.suffix}' (supported: {', '.join(policy.supported_extensions)})")
    if path.stat().st_size == 0:
        raise DocumentReadError("file is empty (0 bytes)")
    with open(path, "rb") as fh:
        head = fh.read(8)
    if head == OLE_MAGIC:
        raise DocumentReadError("old-format (.doc) or password-protected file; not a readable .docx")
    if head[:2] != b"PK":
        raise DocumentReadError("file is corrupt or not a .docx: it is not a ZIP package (a .docx must start with 'PK')")


def read_document(path, policy: Policy = DEFAULT_POLICY) -> List[Block]:
    path = Path(path)
    check_file(path, policy)
    try:
        document = docx.Document(str(path))
    except Exception as exc:  # BadZipFile, KeyError, PackageNotFoundError, ...
        raise DocumentReadError(f"corrupt or invalid .docx ({type(exc).__name__}: {exc})") from exc

    selected = []
    try:
        for part in document.part.package.iter_parts():
            name = str(part.partname)
            for pattern, kind, order in _PART_KINDS:
                if pattern.match(name):
                    selected.append((order, name, kind, part.blob))
                    break
    except Exception as exc:
        raise DocumentReadError(f"cannot read document parts ({type(exc).__name__}: {exc})") from exc
    if not any(k == "body" for _, _, k, _ in selected):
        raise DocumentReadError("no main document part found; not a Word document")

    selected.sort(key=lambda s: (s[0], s[1]))
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    blocks: List[Block] = []
    for _, name, kind, blob in selected:
        try:
            root = etree.fromstring(blob, parser)
        except etree.XMLSyntaxError as exc:
            raise DocumentReadError(f"corrupt XML in {name}: {exc}") from exc
        in_refs = False
        for idx, (p, in_table, in_box) in enumerate(_iter_paragraphs(root), start=1):
            text = normalize_text(_paragraph_text(p, policy.include_deleted_text))
            if text.lower().strip(" :.") in _REF_HEADINGS and len(text) < 30:
                in_refs = True
            entry = bool(_REF_ENTRY.match(text)) or (in_refs and bool(_REF_ENTRY_NUM.match(text)))
            blocks.append(Block(text, name.lstrip("/"), kind, idx, in_table, in_box, entry))
    return blocks
