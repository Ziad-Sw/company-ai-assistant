"""
مسار المعالجة المشترك للمستندات (chunk → embed → store) — المصدر الوحيد لمنطق
الـingestion: بيتستخدم من سكريبت ingest.py (ملفات data/raw) ومن endpoints
الـPhase 3 (رفع/استبدال/إعادة معالجة — ملفات من Supabase Storage).

الفروقات بين المسارين حوالين الـpipeline ده مش جواه:
- السكريبت: الـcategory من الـfrontmatter (إلزامية)، والـidempotency بالـdoc_id+version.
- الـAPI: الـcategory اختيار يدوي من الـadmin (PRD 10.5-ب)، والحالة processing/failed.
"""

from __future__ import annotations

import re
from uuid import UUID

import frontmatter
from pydantic import BaseModel
from supabase import Client

from app.rag.chunking import chunk_markdown
from app.rag.embeddings import embed_document
from app.rag.retrieval import ALL_CATEGORIES

__all__ = [
    "ALL_CATEGORIES",
    "EmptyDocumentError",
    "MissingFrontmatterError",
    "ParsedDocument",
    "parse_markdown_document",
    "process_document",
    "replace_chunks",
]

# مفاتيح الـfrontmatter الإلزامية للـdoc_id/title/version — من غيرهم المستند
# ملوش هوية منطقية (doc_id) ولا version للتعامل مع النسخ المتضاربة (PRD قسم 7).
_REQUIRED_FRONTMATTER_KEYS = ("doc_id", "title", "version")


class MissingFrontmatterError(ValueError):
    """الـfrontmatter ناقص مفاتيح إلزامية — رسالة الـexception جاهزة للعرض."""


class EmptyDocumentError(ValueError):
    """محتوى المستند فاضي — مفيش حاجة تتقسّم لـchunks."""


class ParsedDocument(BaseModel):
    """نتيجة قراية ملف Markdown — الـdoc_id **مش بيتم slugify** (هوية منطقية
    لازم تفضل مطابقة بين النسخ عشان الـidempotency والـreplace)."""

    doc_id: str
    title: str
    version: str
    language: str
    category: str | None
    body: str


def parse_markdown_document(raw_text: str) -> ParsedDocument:
    """
    يقرا الـfrontmatter ويتحقق من المفاتيح الإلزامية.

    Raises:
        MissingFrontmatterError: مفاتيح إلزامية ناقصة (رسالة عربية واضحة).
        EmptyDocumentError: المحتوى بعد الـfrontmatter فاضي.
    """
    post = frontmatter.loads(raw_text)
    meta = post.metadata

    missing = [key for key in _REQUIRED_FRONTMATTER_KEYS if not str(meta.get(key) or "").strip()]
    if missing:
        raise MissingFrontmatterError(
            "ملف الـMarkdown لازم يبدأ بـfrontmatter فيه: "
            f"{', '.join(_REQUIRED_FRONTMATTER_KEYS)} — الناقص: {', '.join(missing)}"
        )

    body = post.content
    if not body.strip():
        raise EmptyDocumentError("محتوى المستند فاضي — مفيش حاجة تتقسّم لـchunks.")

    category = meta.get("category")
    return ParsedDocument(
        doc_id=str(meta["doc_id"]).strip(),
        title=str(meta["title"]).strip(),
        version=str(meta["version"]).strip(),
        language=str(meta.get("language") or "mixed").strip() or "mixed",
        category=category if category in ALL_CATEGORIES else None,
        body=body,
    )


def replace_chunks(sb: Client, document_id: UUID, rows: list[dict]) -> None:
    """يمسح chunks المستند ويكتب الجديدة — عشان إعادة المعالجة ماتكررش البيانات."""
    sb.table("chunks").delete().eq("document_id", str(document_id)).execute()
    if rows:
        sb.table("chunks").insert(rows).execute()


def process_document(sb: Client, document_id: UUID, category: str, body: str) -> int:
    """
    chunk → embed → استبدال chunks المستند في الداتابيز. بيرجّع عدد الـchunks
    ومايلمسش status — المسؤول عن الحالات (processing/active/failed) هو الـcaller.

    Raises:
        EmptyDocumentError: body فاضي (مفيش chunks تتخزن).
        أي exception من Gemini/الداتابيز: بيترفع للـcaller زي ما هو.
    """
    chunks = chunk_markdown(body)
    if not chunks:
        raise EmptyDocumentError("الـchunking مارجّعش chunks — المحتوى مش كافي.")

    rows = []
    for index, chunk in enumerate(chunks):
        rows.append(
            {
                "document_id": str(document_id),
                "content": chunk["content"],
                "embedding": embed_document(chunk["content"]),
                "metadata": {
                    "category": category,
                    "section": chunk["section"],
                    "chunk_index": index,
                },
            }
        )

    # المسح بعد الـembeddings مش قبله (قرار 2026-11-08): لو الـembedding فشل
    # في نص المستند، الـchunks القديمة تفضل موجودة بدل ما المستند يفضل فاضي.
    replace_chunks(sb, document_id, rows)
    return len(rows)


def slugify_for_path(value: str) -> str:
    """
    slug لآمن مسارات الـStorage بس — مش هوية منطقية. يتعامل مع العربي
    (بيطبع المسار مش الـdoc_id المخزّن).
    """
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "doc"
