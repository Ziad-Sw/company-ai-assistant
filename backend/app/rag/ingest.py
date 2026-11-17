"""
سكريبت الـingestion للملفات legacy تحت data/raw/ — سكريبت رقيق استدعاءً.

منطق المعالجة نفسه (chunk → embed → استبدال chunks) عايش في app.rag.pipeline
عشان يبقى مصدر واحد بيتستخدم من السكريبت ده ومن endpoints الـPhase 3.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m app.rag.ingest

الـidempotency: مستند بنفس doc_id وversion مش بيتكرر (upsert)، والـchunks
القديمة بتاعته بتتمسح وتتكتب من جديد.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

from app.db.supabase_client import get_supabase
from app.rag.pipeline import (
    ALL_CATEGORIES,
    EmptyDocumentError,
    MissingFrontmatterError,
    parse_markdown_document,
    process_document,
)

# لازم نحمّل .env الأول قبل أي استدعاء لـget_supabase() أو embed_document(،
# عشان os.environ يبقى فيه القيم من الملف.
load_dotenv()

# backend/app/rag/ingest.py → نطلع 3 مستويات لحد جذر المشروع
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "raw"


def find_markdown_files() -> list[Path]:
    return sorted(DATA_DIR.rglob("*.md"))


def upsert_document(sb, parsed, source_path: str) -> str:
    """يرجّع id المستند — لو موجود بالفعل بنفس doc_id+version بيرجّع الموجود من غير تكرار."""
    existing = (
        sb.table("documents")
        .select("id")
        .eq("doc_id", parsed.doc_id)
        .eq("version", parsed.version)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    result = (
        sb.table("documents")
        .insert(
            {
                "doc_id": parsed.doc_id,
                "title": parsed.title,
                "category": parsed.category,
                "version": parsed.version,
                "language": parsed.language,
                "source_path": source_path,
                "status": "active",
            }
        )
        .execute()
    )
    return result.data[0]["id"]


def ingest_file(sb, path: Path) -> None:
    raw_text = path.read_text(encoding="utf-8")
    try:
        parsed = parse_markdown_document(raw_text)
    except (MissingFrontmatterError, EmptyDocumentError) as exc:
        print(f"⚠️  متجاهل {path.name}: {exc}")
        return

    # السكريبت بيعتمد على category الـfrontmatter (مش اختيار يدوي زي الـAPI) —
    # ملف من غير category معروفة بيتم تجاهله زي الأول.
    if parsed.category not in ALL_CATEGORIES:
        print(f"⚠️  متجاهل {path.name}: category غير معروفة ({parsed.category!r})")
        return

    document_id = upsert_document(sb, parsed, source_path=str(path.relative_to(PROJECT_ROOT)))
    chunks_count = process_document(sb, document_id, parsed.category, parsed.body)
    print(f"📄 {path.name} ({parsed.version}) → ✅ {chunks_count} chunk اتخزّنوا")


def main() -> None:
    sb = get_supabase()
    files = find_markdown_files()
    if not files:
        print(f"مفيش ملفات .md في {DATA_DIR}")
        sys.exit(1)

    print(f"لقيت {len(files)} ملف. بدء الـingestion...\n")
    for path in files:
        ingest_file(sb, path)

    print("\n✅ خلص الـingestion.")


if __name__ == "__main__":
    main()
