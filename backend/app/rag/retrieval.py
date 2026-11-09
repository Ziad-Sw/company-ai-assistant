"""
Permission-aware retrieval: البحث بالتشابه في الـchunks مع فلترة حسب صلاحية الـrole.

فحص الصلاحية هنا كود ثابت (deterministic) — مش قرار LLM (Tech-Stack.md قسم 5).
الـagent ممكن يقترح category، لكن الدالة دي هي اللي بتقرر يتبحث فيها ولا لأ،
والفحص بيحصل **قبل** أي embedding أو query عشان مايتصرفش request على حاجة مرفوضة.

ملحوظة: الاتصال هنا بيتخطى الـRLS (راجع session.py)، فالفلترة دي حالياً هي
طبقة الحماية الوحيدة لحد ما الـRLS policies تتضاف.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import RowMapping, text

from app.db.session import get_session_factory
from app.rag.embeddings import embed_query

ROLE_ALLOWED_CATEGORIES: dict[str, tuple[str, ...]] = {
    "sales": ("property_listings", "payment_policies", "company_info_support"),
    "hr": ("company_info_support",),
    "admin": ("property_listings", "payment_policies", "company_info_support"),
}

ALL_CATEGORIES: frozenset[str] = frozenset().union(*ROLE_ALLOWED_CATEGORIES.values())

MAX_TOP_K = 20

# المستندات الـinactive مش بتظهر في الاسترجاع (PRD قسم 10.5).
# فلتر الـcategory على documents.category (مصدر الحقيقة)، مش على الـmetadata بتاع الـchunk.
_SEARCH_SQL = text(
    """
    SELECT
        c.id AS chunk_id,
        c.content,
        c.metadata,
        d.doc_id,
        d.title AS doc_title,
        d.category,
        d.version,
        d.updated_at,
        d.language,
        c.embedding <=> CAST(:query_embedding AS vector) AS distance
    FROM public.chunks AS c
    JOIN public.documents AS d ON d.id = c.document_id
    WHERE d.category = ANY(:categories)
      AND d.status = 'active'
    ORDER BY distance
    LIMIT :top_k
    """
)


class PermissionDeniedError(Exception):
    """الـrole مش مسموح له يوصل للـcategory المطلوبة."""

    def __init__(self, role: str, category: str) -> None:
        self.role = role
        self.category = category
        super().__init__(
            f"الدور '{role}' غير مسموح له بالوصول لبيانات '{category}'. "
            f"المسموح: {', '.join(ROLE_ALLOWED_CATEGORIES[role])}"
        )


class ChunkMetadata(BaseModel):
    section: dict[str, str]  # {"h2": ..., "h3": ...} من الـheading-aware chunking
    page: int | None  # None للـMarkdown — هيتملا لما نضيف PDF
    version: str
    updated_at: datetime
    language: str


class RetrievedChunk(BaseModel):
    chunk_id: UUID
    content: str
    doc_id: str
    doc_title: str
    category: str
    # similarity = 1 - cosine distance. الـrange النظري [-1, 1]، والأعلى = أقرب
    # للسؤال (عملياً مع Gemini embeddings بيبقى موجب). اخترناه بدل الـdistance
    # الخام عشان "رقم أعلى = أحسن" أوضح للـagent ولتقارير الـevaluation.
    similarity_score: float
    metadata: ChunkMetadata


def resolve_categories(role: str, category: str | None) -> list[str]:
    """
    يحدد الـcategories اللي هيتبحث فيها، أو يرفع exception لو الطلب مرفوض.

    Raises:
        ValueError: role أو category مش معروفين أصلاً.
        PermissionDeniedError: الـcategory معروفة بس الـrole مش مسموح له بيها.
    """
    allowed = ROLE_ALLOWED_CATEGORIES.get(role)
    if allowed is None:
        raise ValueError(f"دور غير معروف: {role!r}")
    if category is None:
        return list(allowed)
    if category not in ALL_CATEGORIES:
        raise ValueError(f"category غير معروفة: {category!r}")
    if category not in allowed:
        raise PermissionDeniedError(role, category)
    return [category]


def retrieve_chunks(
    query: str, role: str, category: str | None = None, top_k: int = 5
) -> list[RetrievedChunk]:
    """
    يرجّع أقرب top_k chunks للسؤال من الـcategories المسموحة للـrole.

    لو category اتحددت: البحث جواها بس (بعد التأكد من الصلاحية).
    لو None: البحث في كل الـcategories المسموحة للـrole.

    Raises:
        ValueError: role/category مش معروفين، أو top_k برا [1, MAX_TOP_K].
        PermissionDeniedError: الـrole مش مسموح له بالـcategory المطلوبة.
    """
    if not 1 <= top_k <= MAX_TOP_K:
        raise ValueError(f"top_k لازم يكون بين 1 و{MAX_TOP_K}، جالنا {top_k}")
    categories = resolve_categories(role, category)
    # بنجيب الـsession factory قبل الـembedding: لو DATABASE_URL ناقص نفشل فوراً
    # من غير ما نصرف request من حدود Gemini على بحث مش هيكمل.
    session_factory = get_session_factory()

    query_embedding = _to_vector_literal(embed_query(query))
    with session_factory() as session:
        rows = session.execute(
            _SEARCH_SQL,
            {"query_embedding": query_embedding, "categories": categories, "top_k": top_k},
        ).mappings()
        return [_row_to_chunk(row) for row in rows]


def _to_vector_literal(embedding: list[float]) -> str:
    """يحوّل الـvector لصيغة pgvector النصية '[x,y,...]' (بيتبعت كـbind parameter)."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


def _row_to_chunk(row: RowMapping) -> RetrievedChunk:
    chunk_meta = row["metadata"]
    return RetrievedChunk(
        chunk_id=row["chunk_id"],
        content=row["content"],
        doc_id=row["doc_id"],
        doc_title=row["doc_title"],
        category=row["category"],
        similarity_score=1 - row["distance"],
        metadata=ChunkMetadata(
            section=chunk_meta.get("section", {}),
            page=chunk_meta.get("page"),
            version=row["version"],
            updated_at=row["updated_at"],
            language=row["language"],
        ),
    )
