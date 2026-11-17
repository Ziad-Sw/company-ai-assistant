"""
استخراج النص من صيغ الملفات المختلفة (PRD 10.5-ب: PDF/DOCX/Markdown) —
الطبقة الوحيدة اللي بتعرف الصيغ؛ الـpipeline اللي فوقها بيشتغل على نص بس.

- .md/.txt: نص UTF-8 مباشرة.
- .pdf: pypdf — استخراج نص الصفحات بالترتيب.
- .docx: python-docx — الفقرات بالترتيب + محتوى الجداول (خلية بخط فاصل).

الـMarkdown بيحتفظ بمساره الخاص (frontmatter إلزامي — هوية ونسخ)،
وباقي الصيغ بياخدوا هوية تلقائية من اسم الملف (قرار 2026-11-17).
"""

from __future__ import annotations

import io

SUPPORTED_EXTENSIONS = frozenset({".md", ".txt", ".pdf", ".docx"})


class UnsupportedFormatError(ValueError):
    """صيغة مش مدعومة — رسالة الـexception جاهزة للعرض (422)."""


class ExtractionError(ValueError):
    """الملف بصيغة مدعومة بس مش بايتات صالحة ليها (PDF تالف / مش UTF-8)."""


def extract_text(extension: str, raw: bytes) -> str:
    """
    يرجّع نص المستند من البايتات حسب الامتداد (حرف صغير مع النقطة).

    Raises:
        UnsupportedFormatError: امتداد خارج القايمة.
        ExtractionError: الملف مش متوافق مع صيغته (تالف/ترميز غلط).
    """
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError("الصيغ المدعومة: PDF، DOCX، Markdown (.md)، أو TXT.")

    if extension in (".md", ".txt"):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExtractionError("الملف مش نص UTF-8 صالح.") from exc

    if extension == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(raw))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # noqa: BLE001 — pypdf بيرمي أنواع كتير لملف تالف
            raise ExtractionError("ملف الـPDF مش صالح أو مش قابل للقراية.") from exc
        return "\n\n".join(page for page in pages if page.strip())

    # .docx — الفقرات بالترتيب، وجداول المستند بعد الفقرات (مخططات السداد
    # والمواصفات في مستندات الشركات غالباً جداول — تخطيها بيفقد معلومات
    # أساسية من الـretrieval).
    from docx import Document

    try:
        document = Document(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 — python-docx بيرمي أنواع كتير لملف تالف
        raise ExtractionError("ملف الـDOCX مش صالح أو مش قابل للقراية.") from exc

    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n\n".join(parts)
