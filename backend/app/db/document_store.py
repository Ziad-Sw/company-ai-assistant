"""
عمليات المستندات على Postgres (نفس نمط conversation_store) — قراية/تعديل صفوف
public.documents. كتابة الـchunks نفسها في supabase_client/pipeline (service_role)
عشان الـvector بالـ768 dims وبيتكتب كمصفوفة مباشرة.

كل الـSQL هنا بـbind params (:name) — مفيش أي f-string في الـqueries نفسها.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_session_factory

__all__ = [
    "DocumentSummary",
    "create_document",
    "deactivate_other_versions",
    "delete_document",
    "find_document",
    "find_document_id_by_version",
    "list_document_versions",
    "list_documents",
    "set_document_category",
    "set_document_status",
]

class DocumentSummary(BaseModel):
    id: UUID
    doc_id: str
    title: str
    category: str
    version: str
    language: str
    status: str
    uploaded_by_name: str | None
    updated_at: datetime
    created_at: datetime


_LIST_SELECT = """
SELECT d.id, d.doc_id, d.title, d.category, d.version, d.language, d.status,
       p.full_name AS uploaded_by_name, d.updated_at, d.created_at
FROM public.documents d
LEFT JOIN public.profiles p ON p.id = d.uploaded_by
"""


def _row_to_summary(row: Any) -> DocumentSummary:
    return DocumentSummary(
        id=row.id,
        doc_id=row.doc_id,
        title=row.title,
        category=row.category,
        version=row.version,
        language=row.language,
        status=row.status,
        uploaded_by_name=row.uploaded_by_name,
        updated_at=row.updated_at,
        created_at=row.created_at,
    )


def list_documents(category: str | None = None, search: str | None = None) -> list[DocumentSummary]:
    """قائمة المستندات مع اسم الـuploader (PRD 10.5-أ: مين رفعه) — الأحدث تحديثاً أولاً.

    الـcategory اللي بييجي هنا متحقق منها ضد allowlist في الـendpoint، والـsearch
    بيتخزن كـbind param (الـ%/wildcards بتتعامل بالحرف — مساحة admin بس).
    """
    conditions: list[str] = []
    params: dict[str, Any] = {}
    if category:
        conditions.append("d.category = :category")
        params["category"] = category
    if search:
        conditions.append("(d.title ILIKE :search OR d.doc_id ILIKE :search)")
        params["search"] = f"%{search}%"

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"{_LIST_SELECT} {where_clause} ORDER BY d.updated_at DESC"

    with get_session_factory().begin() as session:
        rows = session.execute(text(sql), params).fetchall()
    return [_row_to_summary(row) for row in rows]


def find_document(document_id: UUID) -> DocumentSummary | None:
    with get_session_factory().begin() as session:
        row = session.execute(
            text(f"{_LIST_SELECT} WHERE d.id = :document_id"),
            {"document_id": document_id},
        ).first()
    return _row_to_summary(row) if row else None


def find_document_id_by_version(doc_id: str, version: str) -> UUID | None:
    """للتحقق من تكرار doc_id+version قبل الرفع/الاستبدال (PRD قسم 7: تضارب النسخ)."""
    with get_session_factory().begin() as session:
        row = session.execute(
            text("SELECT id FROM public.documents WHERE doc_id = :doc_id AND version = :version"),
            {"doc_id": doc_id, "version": version},
        ).scalar()
    return row


def create_document(
    *,
    doc_id: str,
    title: str,
    category: str,
    version: str,
    language: str,
    source_path: str,
    uploaded_by: UUID,
    status: str = "processing",
) -> UUID:
    with get_session_factory().begin() as session:
        document_id = session.execute(
            text(
                """
                INSERT INTO public.documents
                  (doc_id, title, category, version, language, status, source_path, uploaded_by)
                VALUES
                  (:doc_id, :title, :category, :version, :language, :status, :source_path, :uploaded_by)
                RETURNING id
                """
            ),
            {
                "doc_id": doc_id,
                "title": title,
                "category": category,
                "version": version,
                "language": language,
                "status": status,
                "source_path": source_path,
                "uploaded_by": uploaded_by,
            },
        ).scalar_one()
    return document_id


def set_document_status(document_id: UUID, status: str) -> None:
    """بيغيّر الحالة — بحدّث updated_at كمان (PRD 10.5: عمود تاريخ آخر تحديث)."""
    with get_session_factory().begin() as session:
        session.execute(
            text(
                """
                UPDATE public.documents
                SET status = :status, updated_at = now()
                WHERE id = :document_id
                """
            ),
            {"status": status, "document_id": document_id},
        )


def set_document_category(document_id: UUID, category: str) -> None:
    """
    بيتغيّر category المستند + metadata.category في كل الـchunks بنفس الـUPDATE
    اللوجيكي (jsonb_set — من غير إعادة embedding): الـretrieval بيلم chunks بـ
    documents.category مباشرة، لكن الـmetadata المخزّنة لازم تفضل مطابقة.
    """
    with get_session_factory().begin() as session:
        session.execute(
            text(
                """
                UPDATE public.documents
                SET category = :category, updated_at = now()
                WHERE id = :document_id
                """
            ),
            {"category": category, "document_id": document_id},
        )
        session.execute(
            text(
                """
                UPDATE public.chunks
                SET metadata = jsonb_set(metadata, '{category}', to_jsonb(:category))
                WHERE document_id = :document_id
                """
            ),
            {"category": category, "document_id": document_id},
        )


def deactivate_other_versions(doc_id: str, keep_document_id: UUID) -> int:
    """
    بعد نجاح استبدال/رفع نسخة جديدة بنفس doc_id: كل النسخ التانية (بما فيها
    النسخ اللي كانت active) بتتفعّل inactive — العميل لازم يشوف نسخة واحدة
    active لكل doc_id (PRD قسم 7: تضارب النسخ — كمان بتصحح النزاع المزدوج
    الموجود فعلياً في 2025.1/2026.1).
    """
    with get_session_factory().begin() as session:
        result = session.execute(
            text(
                """
                UPDATE public.documents
                SET status = 'inactive', updated_at = now()
                WHERE doc_id = :doc_id
                  AND id <> :keep_document_id
                  AND status = 'active'
                """
            ),
            {"doc_id": doc_id, "keep_document_id": keep_document_id},
        )
    return result.rowcount


def list_document_versions(doc_id: str) -> list[DocumentSummary]:
    """كل نسخ نفس الـdoc_id — للـversion history في الـmodal (PRD 10.5-ب)."""
    with get_session_factory().begin() as session:
        rows = session.execute(
            text(f"{_LIST_SELECT} WHERE d.doc_id = :doc_id ORDER BY d.created_at DESC"),
            {"doc_id": doc_id},
        ).fetchall()
    return [_row_to_summary(row) for row in rows]


def delete_document(document_id: UUID) -> None:
    """حذف نهائي — chunks بتتمسح cascade (schema.sql). بيتنفّذ قبل مسح الملف."""
    with get_session_factory().begin() as session:
        session.execute(text("DELETE FROM public.documents WHERE id = :document_id"), {"document_id": document_id})
