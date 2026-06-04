from __future__ import annotations

from pathlib import Path


def export_txt(path: str | Path, text: str) -> None:
    Path(path).write_text(text or "", encoding="utf-8")


def export_docx(path: str | Path, text: str) -> None:
    from docx import Document

    doc = Document()
    for para in (text or "").split("\n"):
        doc.add_paragraph(para)
    doc.save(str(path))
