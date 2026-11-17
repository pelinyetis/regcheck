"""Extract plain text (paragraphs + tables, in document order) from a .docx.
This is what the agent receives as input — UiPath would pass the same text.
Usage: uv run --no-project --with python-docx python scripts/docx_to_text.py <file.docx> [out.txt]
"""
import sys
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def docx_text(path: str) -> str:
    doc = Document(path)
    lines = []
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            para = Paragraph(child, doc)
            t = para.text.strip()
            if not t:
                continue
            if para.style is not None and para.style.name.startswith("List"):
                t = "- " + t
            elif para._p.pPr is not None and para._p.pPr.numPr is not None:
                t = "- " + t
            lines.append(t)
        elif tag == "tbl":
            for row in Table(child, doc).rows:
                lines.append("| " + " | ".join(c.text.strip() for c in row.cells) + " |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    text = docx_text(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(text)
    else:
        print(text)
