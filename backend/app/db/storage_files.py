"""
قراية/كتابة ملفات المستندات — مسارين للمصدر:

- ملفات الـPhase 3: "<doc_id-slug>/<version>/<filename>" في Supabase Storage
  (bucket: documents — خاص، created في migrations/003).
- ملفات legacy من سكريبت ingest: مسارات "data/raw/..." على ديسك المشروع
  (source_path القديم قبل وجود الـStorage).

الـfrontend عمره ما بيوصل للـStorage مباشرة — الـbackend بيعمل ده بـservice_role.
"""

from __future__ import annotations

import logging
from pathlib import Path

from supabase import Client

from app.rag.pipeline import slugify_for_path

logger = logging.getLogger(__name__)

DOCUMENTS_BUCKET = "documents"
LEGACY_DATA_PREFIX = "data/"

# جذر المشروع: backend/app/db/storage_files.py → parents[3] = D:\Company-AI-Assistant
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# حد الـbucket نفسه (20 MB في migrations/003) — نفس الرقم هنا كتحقق أسرع قبل الرفع
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def storage_path(doc_id: str, version: str, filename: str) -> str:
    """
    مسار آمن داخل الـbucket: doc_id بيتslugify (الـdoc_id العربي بيطلع مسار
    لاتيني، مش بيتغير الـdoc_id المنطقي المخزّن)، وfilename بيتخلص من أي
    directory traversal قبل ما يلمس الـpath.
    """
    safe_filename = Path(filename).name
    return f"{slugify_for_path(doc_id)}/{version}/{safe_filename}"


def upload_document_file(sb: Client, path: str, data: bytes) -> None:
    """يرفع الملف للـbucket — أي failure بيرفع exception للـcaller (HTTP 502)."""
    sb.storage.from_(DOCUMENTS_BUCKET).upload(path, data)


def read_document_file(sb: Client, source_path: str) -> bytes:
    """
    يقرا الملف من المصدر الصحيح حسب شكل المسار — legacy من الديسك، جديد من الـStorage.

    Raises:
        FileNotFoundError: ملف legacy مش موجود على الديسك.
        StorageException: ملف Storage مش موجود أو الرفع فشل.
    """
    if source_path.startswith(LEGACY_DATA_PREFIX):
        return (PROJECT_ROOT / source_path).read_bytes()
    return sb.storage.from_(DOCUMENTS_BUCKET).download(source_path)


def delete_document_file_best_effort(sb: Client, source_path: str | None) -> None:
    """
    يمسح الملف بعد حذف صف المستند — مسح المستند مش فاشل لو الملف ضاع
    (الصحيح ترتيبهم كده: الـDB هو مصدر الحقيقة، الملف مشهود مش أساسي).
    """
    if not source_path:
        return
    try:
        if source_path.startswith(LEGACY_DATA_PREFIX):
            (PROJECT_ROOT / source_path).unlink(missing_ok=True)
        else:
            sb.storage.from_(DOCUMENTS_BUCKET).remove([source_path])
    except Exception:  # noqa: BLE001 — مسح الملفات مساعد، مش شرط نجاحه
        logger.exception("مقدرتش أمسح ملف المستند: %s", source_path)
