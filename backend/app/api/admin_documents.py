"""
Endpoints إدارة المستندات (Phase 3 — PRD 10.5) — كلها للـadmin بس عبر require_admin.

الدورة الحياتية: الرفع/الاستبدال/إعادة المعالجة بيخليوا الصف processing →
BackgroundTask بيchunks وembeds → active (أو failed من غير ما الملف يتلمس).
الـfrontend بيعمل polling على GET /{id} لحد ما الحالة تغيب عن processing
(قرار معتمد: processing بسيط بالـBackgroundTasks — مش Celery).

السجلات: كل عملية بتتسجل في audit_logs (مين عمل إيه وإمتى) — delete بيتسجل
بعد المسح عشان سجل حذف حاجة مش موجودة يفضل منطقي.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from supabase import StorageException

from app.auth.dependencies import AuthenticatedUser, require_admin
from app.db import audit_store, document_store
from app.db.storage_files import (
    MAX_UPLOAD_BYTES,
    delete_document_file_best_effort,
    read_document_file,
    storage_path,
    upload_document_file,
)
from app.db.supabase_client import get_supabase
from app.rag.pipeline import (
    ALL_CATEGORIES,
    EmptyDocumentError,
    MissingFrontmatterError,
    parse_markdown_document,
    process_document,
)
from app.rag.retrieval import ROLE_ALLOWED_CATEGORIES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/documents",
    tags=["admin-documents"],
    dependencies=[Depends(require_admin)],
)

# ملاحظة الـrouter: dependencies على مستوى الـrouter بتتنفذ قبل الـendpoint —
# كل endpoint هنا محمي admin افتراضياً بدون ما يتكرر.

_NOT_FOUND_MESSAGE = "المستند مش موجود."
_PROCESSING_MESSAGE = "المستند بيتعالج دلوقتي — استنى يخلص أو جرب تاني بعد شوية."
_INVALID_CATEGORY_MESSAGE = f"الـcategory مش من القائمة: {', '.join(sorted(ALL_CATEGORIES))}."
_UNSUPPORTED_FILE_MESSAGE = "الصيغة المدعومة دلوقتي: Markdown (.md) بس."
_TOO_LARGE_MESSAGE = "الملف أكبر من الحد المسموح (20 MB)."
_INVALID_ENCODING_MESSAGE = "الملف مش نص UTF-8 صالح."
_NO_CHANGES_MESSAGE = "مفيش تغييرات في الطلب."
_DUPLICATE_VERSION_MESSAGE = "النسخة دي موجودة بالفعل لنفس المستند."
_DOC_ID_MISMATCH_MESSAGE = "الـdoc_id في الملف مش مطابق للمستند اللي بيتم استبداله."
_SOURCE_MISSING_MESSAGE = "ملف المصدر مش متاح لإعادة المعالجة."
_STORAGE_FAILED_MESSAGE = "فشل تخزين الملف — جرب تاني."

_ALLOWED_SOURCE_EXTENSIONS = {".md"}


class DocumentPatch(BaseModel):
    """تعديلات مسموحة على المستند — الحالة بتتغير بين active/inactive فقط؛
    processing/failed بتتتحكم فيهم بالرفع وإعادة المعالجة وحدهم."""

    category: str | None = None
    status: Literal["active", "inactive"] | None = None


def _validate_category(category: str) -> str:
    if category not in ROLE_ALLOWED_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_INVALID_CATEGORY_MESSAGE)
    return category


def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    """تحقق الصيغة/الحجم/الترميز ثم يرجّع (النص، البايتات الأصلية) — البايتات
    بتترفع للـStorage زي ما هي، النص بيتparse. القراءة مرة واحدة."""
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if f".{extension}" not in _ALLOWED_SOURCE_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_UNSUPPORTED_FILE_MESSAGE)

    raw = file.file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_TOO_LARGE_MESSAGE)

    try:
        return raw.decode("utf-8"), raw
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_INVALID_ENCODING_MESSAGE
        ) from exc


def _parse_or_422(raw_text: str):
    try:
        return parse_markdown_document(raw_text)
    except (MissingFrontmatterError, EmptyDocumentError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


def _assert_not_processing(document: document_store.DocumentSummary) -> None:
    """الحماية من التعديل على مستند نصف معالج — البيانات ممكن تكون لسه بتتكتب."""
    if document.status == "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PROCESSING_MESSAGE)


# ─── Background tasks — sync (threadpool) بيقروا/يكتبوا الداتابيز والـGemini ──

def _run_processing(document_id: UUID, category: str, body: str) -> None:
    """معالجة نسخة واحدة: chunk → embed → استبدال chunks → active. أي فشل = failed."""
    try:
        process_document(get_supabase(), document_id, category, body)
        document_store.set_document_status(document_id, "active")
    except Exception:  # noqa: BLE001 — كل فشل لوجيكي لازم يرجّع الصف من processing
        logger.exception("المعالجة فشلت للمستند %s", document_id)
        document_store.set_document_status(document_id, "failed")


def _run_replace_processing(new_document_id: UUID, doc_id: str, category: str, body: str) -> None:
    """معالجة نسخة استبدال — النجاح بس بيفعّل deactivation للنسخ القديمة؛
    الفشل بيسيب النسخة القديمة active (المستند مش بيضيع بسبب معالجة جديد)."""
    try:
        process_document(get_supabase(), new_document_id, category, body)
        document_store.set_document_status(new_document_id, "active")
        document_store.deactivate_other_versions(doc_id, keep_document_id=new_document_id)
    except Exception:  # noqa: BLE001 — نفس مبدأ _run_processing
        logger.exception("معالجة الاستبدال فشلت للنسخة الجديدة %s", new_document_id)
        document_store.set_document_status(new_document_id, "failed")


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("", response_model=list[document_store.DocumentSummary])
def list_documents(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    category: str | None = None,
    search: str | None = None,
) -> list[document_store.DocumentSummary]:
    if category:
        _validate_category(category)
    return document_store.list_documents(category=category, search=search)


@router.post("", response_model=document_store.DocumentSummary, status_code=status.HTTP_201_CREATED)
def upload_document(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    category: Annotated[str, Form()],
) -> document_store.DocumentSummary:
    """رفع مستند جديد — الـcategory اختيار يدوي من الـadmin (PRD 10.5-ب)."""
    _validate_category(category)
    raw_text, raw_bytes = _read_upload(file)
    parsed = _parse_or_422(raw_text)
    if document_store.find_document_id_by_version(parsed.doc_id, parsed.version):
        # نفس doc_id+version مسجل بالفعل — الرفع المكرر بيعمل نسختين active
        # فتدخل chunks مكررة في الـretrieval (PRD قسم 7: تضارب النسخ).
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_VERSION_MESSAGE)

    path = storage_path(parsed.doc_id, parsed.version, file.filename or "")
    try:
        # الرفع قبل إنشاء الصف: لو الـStorage فشل مفيش صف processing عايش بلا ملف.
        upload_document_file(get_supabase(), path, raw_bytes)
    except StorageException as exc:
        logger.exception("رفع الملف للـStorage فشل: %s", path)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=_STORAGE_FAILED_MESSAGE) from exc

    document_id = document_store.create_document(
        doc_id=parsed.doc_id,
        title=parsed.title,
        category=category,
        version=parsed.version,
        language=parsed.language,
        source_path=path,
        uploaded_by=admin.user_id,
    )
    audit_store.record_audit(admin.user_id, "upload", "document", document_id)
    background_tasks.add_task(_run_processing, document_id, category, parsed.body)

    summary = document_store.find_document(document_id)
    if summary is None:  # pragma: no cover — الصف اتعمل في نفس الـrequest
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_NOT_FOUND_MESSAGE)
    return summary


@router.get("/{document_id}", response_model=document_store.DocumentSummary)
def get_document(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    document_id: UUID,
) -> document_store.DocumentSummary:
    """poll endpoint — الـfrontend بيسأل هنا لحد ما الحالة تبقى active/failed."""
    document = document_store.find_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    return document


@router.patch("/{document_id}", response_model=document_store.DocumentSummary)
def patch_document(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    document_id: UUID,
    patch: DocumentPatch,
) -> document_store.DocumentSummary:
    """تعديل الـcategory والحالة من غير إعادة معالجة — البيانات (chunks) مش بتتلمس
    غير في jsonb_set للـmetadata.category. الحالة processing ممنوع التعديل عليها."""
    document = document_store.find_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    _assert_not_processing(document)

    if patch.category is None and patch.status is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_NO_CHANGES_MESSAGE)

    if patch.category and patch.category != document.category:
        _validate_category(patch.category)
        document_store.set_document_category(document_id, patch.category)
        audit_store.record_audit(admin.user_id, "edit", "document", document_id)

    if patch.status and patch.status != document.status:
        document_store.set_document_status(document_id, patch.status)
        action = "activate" if patch.status == "active" else "deactivate"
        audit_store.record_audit(admin.user_id, action, "document", document_id)

    updated = document_store.find_document(document_id)
    if updated is None:  # pragma: no cover — الصف اتعمل للتو في نفس الـrequest
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    return updated


@router.post("/{document_id}/replace", response_model=document_store.DocumentSummary, status_code=status.HTTP_201_CREATED)
def replace_document(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    background_tasks: BackgroundTasks,
    document_id: UUID,
    file: Annotated[UploadFile, File()],
) -> document_store.DocumentSummary:
    """استبدال نسخة موجودة بملف جديد — نسخة جديدة بنفس doc_id، والقديمة تفضل
    active لحد ما الجديدة تبقى active (قرار 2026-11-08)."""
    target = document_store.find_document(document_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    _assert_not_processing(target)

    raw_text, raw_bytes = _read_upload(file)
    parsed = _parse_or_422(raw_text)
    if parsed.doc_id != target.doc_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_DOC_ID_MISMATCH_MESSAGE)
    if document_store.find_document_id_by_version(target.doc_id, parsed.version):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_VERSION_MESSAGE)

    path = storage_path(target.doc_id, parsed.version, file.filename or "")
    try:
        upload_document_file(get_supabase(), path, raw_bytes)
    except StorageException as exc:
        logger.exception("رفع الملف للـStorage فشل: %s", path)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=_STORAGE_FAILED_MESSAGE) from exc

    new_id = document_store.create_document(
        doc_id=target.doc_id,
        title=parsed.title,
        category=target.category,  # الـcategory بتاع المستند الحالي هو المرجع
        version=parsed.version,
        language=parsed.language,
        source_path=path,
        uploaded_by=admin.user_id,
    )
    # الـaudit للاستبدال على الـtarget الأصلي (PRD 10.5-د: سجل الاستبدال على المستند القديم).
    audit_store.record_audit(admin.user_id, "replace", "document", document_id)
    background_tasks.add_task(_run_replace_processing, new_id, target.doc_id, target.category, parsed.body)

    summary = document_store.find_document(new_id)
    if summary is None:  # pragma: no cover — الصف اتعمل للتو في نفس الـrequest
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    return summary


@router.post("/{document_id}/reprocess", response_model=document_store.DocumentSummary)
def reprocess_document(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    background_tasks: BackgroundTasks,
    document_id: UUID,
) -> document_store.DocumentSummary:
    """إعادة معالجة نفس الملف (source_path) من غير رفع جديد — للـfailed القديم
    أو للمستندات اللي الـchunks بتاعتها فسدت."""
    document = document_store.find_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    _assert_not_processing(document)

    if not document.source_path:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_SOURCE_MISSING_MESSAGE)

    try:
        raw = read_document_file(get_supabase(), document.source_path)
    except (StorageException, OSError) as exc:
        logger.exception("قراية مصدر المستند فشلت: %s", document.source_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_SOURCE_MISSING_MESSAGE
        ) from exc

    try:
        raw_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_INVALID_ENCODING_MESSAGE
        ) from exc

    parsed = _parse_or_422(raw_text)
    document_store.set_document_status(document_id, "processing")
    audit_store.record_audit(admin.user_id, "reprocess", "document", document_id)
    background_tasks.add_task(_run_processing, document_id, document.category, parsed.body)

    summary = document_store.find_document(document_id)
    if summary is None:  # pragma: no cover — الصف مش بيتمسح في المسار ده
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    return summary


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_endpoint(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    document_id: UUID,
) -> None:
    """حذف نهائي — chunks cascade في الـDB، الملف best-effort، والسجل بيفضل موجود."""
    document = document_store.find_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    _assert_not_processing(document)

    document_store.delete_document(document_id)
    delete_document_file_best_effort(get_supabase(), document.source_path)
    # السجل بعد المسح عشان صف المستند مش موجود بس الـaudit باقي — تصميم الـschema
    # (target_id من غير FK) بيسمح بالـorder ده.
    audit_store.record_audit(admin.user_id, "delete", "document", document_id)


@router.get("/{document_id}/versions", response_model=list[document_store.DocumentSummary])
def list_document_versions(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    document_id: UUID,
) -> list[document_store.DocumentSummary]:
    """كل نسخ نفس doc_id (الأحدث أولاً) — للـversion history modal (PRD 10.5-ب)."""
    document = document_store.find_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    return document_store.list_document_versions(document.doc_id)


@router.get("/{document_id}/audit", response_model=list[audit_store.AuditEntry])
def get_document_audit(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    document_id: UUID,
) -> list[audit_store.AuditEntry]:
    """سجل الـaudit للمستند — لسه شغال حتى بعد حذف المستند (PRD 10.5-د):
    المستند مش موجود + مفيش سجل = 404 (id عشوائي)، المستند مش موجود + سجل موجود
    = 200 (مستند متمسح لسه تاريخه متاح)."""
    entries = audit_store.list_target_audit("document", document_id)
    if document_store.find_document(document_id) is None and not entries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_MESSAGE)
    return entries
