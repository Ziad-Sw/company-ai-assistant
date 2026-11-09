"""
سكريبت الـingestion الكامل: extract → chunk → embed → store.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m app.rag.ingest

بيمشي على كل ملفات .md تحت data/raw/<category>/، يقسّمها لـchunks،
يحوّلها لـvectors، ويخزّنها في Supabase. لو شغّلت السكريبت أكتر من
مرة، مستند بنفس doc_id وversion مش بيتكرر (upsert بالـdoc_id+version)،
والـchunks القديمة بتاعته بتتمسح وتتكتب من جديد بدل ما تتكرر.
"""

from __future__ import annotations

import sys
from pathlib import Path

import frontmatter
from dotenv import load_dotenv

from app.db.supabase_client import get_supabase
from app.rag.chunking import chunk_markdown
from app.rag.embeddings import embed_document

# لازم نحمّل .env الأول قبل أي استدعاء لـget_supabase() أو embed_document(،
# عشان os.environ يبقى فيه القيم من الملف.
load_dotenv()

# backend/app/rag/ingest.py → نطلع 3 مستويات لحد جذر المشروع
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "raw"

VALID_CATEGORIES = {"property_listings", "payment_policies", "company_info_support"}


def find_markdown_files() -> list[Path]:
    return sorted(DATA_DIR.rglob("*.md"))


def upsert_document(sb, meta: dict, source_path: str) -> str:
    """يرجّع id المستند — لو موجود بالفعل بنفس doc_id+version بيرجّع الموجود من غير تكرار."""
    existing = (
        sb.table("documents")
        .select("id")
        .eq("doc_id", meta["doc_id"])
        .eq("version", meta["version"])
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    result = (
        sb.table("documents")
        .insert(
            {
                "doc_id": meta["doc_id"],
                "title": meta["title"],
                "category": meta["category"],
                "version": meta["version"],
                "language": meta.get("language", "mixed"),
                "source_path": source_path,
                "status": "active",
            }
        )
        .execute()
    )
    return result.data[0]["id"]


def replace_chunks(sb, document_id: str, rows: list[dict]) -> None:
    """يمسح chunks المستند القديمة ويكتب الجديدة — عشان إعادة التشغيل ماتكررش البيانات."""
    sb.table("chunks").delete().eq("document_id", document_id).execute()
    if rows:
        sb.table("chunks").insert(rows).execute()


def ingest_file(sb, path: Path) -> None:
    post = frontmatter.load(path)
    meta = post.metadata
    body = post.content

    if meta.get("category") not in VALID_CATEGORIES:
        print(f"⚠️  متجاهل {path.name}: category غير معروفة ({meta.get('category')!r})")
        return

    document_id = upsert_document(sb, meta, source_path=str(path.relative_to(PROJECT_ROOT)))

    chunks = chunk_markdown(body)
    print(f"📄 {path.name} ({meta['version']}) → {len(chunks)} chunk")

    rows = []
    for i, chunk in enumerate(chunks):
        vector = embed_document(chunk["content"])
        rows.append(
            {
                "document_id": document_id,
                "content": chunk["content"],
                "embedding": vector,
                "metadata": {
                    "category": meta["category"],
                    "section": chunk["section"],
                    "chunk_index": i,
                },
            }
        )

    # المسح بعد الـembedding مش قبله: لو الـembedding فشل في النص،
    # الـchunks القديمة تفضل موجودة بدل ما المستند يفضل من غير chunks خالص.
    replace_chunks(sb, document_id, rows)
    if rows:
        print(f"   ✅ {len(rows)} chunk اتخزّنوا")


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