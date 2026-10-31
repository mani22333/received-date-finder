"""Build small, valid .docx files for tests (no network, no templates).

spec keys: body, header, footer, footnotes, endnotes, comments
body items: "text" | ("runs", [..]) | ("table", rows) | ("textbox", "text")
            | ("ins", "text") | ("del", "text") | ("br", [line1, line2])
table rows: list of rows; a cell is "text" or ("table", rows) for a nested table
"""
import zipfile
from xml.sax.saxutils import escape

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
      'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
      'xmlns:v="urn:schemas-microsoft-com:vml"')
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "application/vnd.openxmlformats-officedocument.wordprocessingml"


def _run(text):
    return f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _para(text):
    return f"<w:p>{_run(text)}</w:p>"


def _item(it):
    if isinstance(it, str):
        return _para(it)
    kind, val = it
    if kind == "runs":
        runs = "".join(f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{escape(t)}</w:t></w:r>' if i % 2 else _run(t)
                       for i, t in enumerate(val))
        return f"<w:p>{runs}</w:p>"
    if kind == "br":
        return "<w:p>" + '<w:r><w:br/></w:r>'.join(_run(t) for t in val) + "</w:p>"
    if kind == "ins":
        return f'<w:p><w:ins w:id="1" w:author="a" w:date="2026-01-01T00:00:00Z">{_run(val)}</w:ins></w:p>'
    if kind == "del":
        return (f'<w:p><w:del w:id="2" w:author="a" w:date="2026-01-01T00:00:00Z"><w:r>'
                f'<w:delText xml:space="preserve">{escape(val)}</w:delText></w:r></w:del></w:p>')
    if kind == "textbox":
        inner = f"<w:txbxContent>{_para(val)}</w:txbxContent>"
        return ("<w:p><w:r><mc:AlternateContent><mc:Choice Requires=\"wps\"><w:drawing><wps:wsp><wps:txbx>"
                f"{inner}</wps:txbx></wps:wsp></w:drawing></mc:Choice><mc:Fallback><w:pict><v:shape>"
                f"<v:textbox>{inner}</v:textbox></v:shape></w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>")
    if kind == "table":
        return _table(val)
    raise ValueError(kind)


def _table(rows):
    out = ["<w:tbl><w:tblPr/><w:tblGrid/>"]
    for row in rows:
        out.append("<w:tr>")
        for cell in row:
            out.append("<w:tc>" + (_table(cell[1]) + "<w:p/>" if isinstance(cell, tuple) else _para(cell)) + "</w:tc>")
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def _wrap(root, inner):
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:{root} {NS}>{inner}</w:{root}>'


def make_docx(path, spec=None):
    spec = spec or {}
    body = "".join(_item(i) for i in spec.get("body", [])) or "<w:p/>"
    parts = {"word/document.xml": _wrap("document", f"<w:body>{body}<w:sectPr/></w:body>")}
    rels, overrides = [], [("/word/document.xml", "document.main+xml")]

    def add(rid, name, rel, ctype, xml):
        parts[f"word/{name}"] = xml
        rels.append(f'<Relationship Id="{rid}" Type="{REL}/{rel}" Target="{name}"/>')
        overrides.append((f"/word/{name}", ctype))

    if spec.get("header"):
        add("rId11", "header1.xml", "header", "header+xml", _wrap("hdr", "".join(_item(i) for i in spec["header"])))
    if spec.get("footer"):
        add("rId12", "footer1.xml", "footer", "footer+xml", _wrap("ftr", "".join(_item(i) for i in spec["footer"])))
    if spec.get("footnotes"):
        notes = "".join(f'<w:footnote w:id="{n}">{_para(t)}</w:footnote>' for n, t in enumerate(spec["footnotes"], 1))
        add("rId13", "footnotes.xml", "footnotes", "footnotes+xml", _wrap("footnotes", notes))
    if spec.get("endnotes"):
        notes = "".join(f'<w:endnote w:id="{n}">{_para(t)}</w:endnote>' for n, t in enumerate(spec["endnotes"], 1))
        add("rId14", "endnotes.xml", "endnotes", "endnotes+xml", _wrap("endnotes", notes))
    if spec.get("comments"):
        notes = "".join(f'<w:comment w:id="{n}" w:author="a">{_para(t)}</w:comment>' for n, t in enumerate(spec["comments"], 1))
        add("rId15", "comments.xml", "comments", "comments+xml", _wrap("comments", notes))

    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     + "".join(f'<Override PartName="{p}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{c}"/>'
                               for p, c in overrides) + "</Types>")
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 f'<Relationship Id="rId1" Type="{REL}/officeDocument" Target="word/document.xml"/></Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                + "".join(rels) + "</Relationships>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        for name, xml in parts.items():
            z.writestr(name, xml)
    return path
