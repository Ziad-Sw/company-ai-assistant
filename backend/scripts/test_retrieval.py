"""
اختبار يدوي للـpermission-aware retrieval على الداتابيز الحقيقية.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة، وDATABASE_URL في الـ.env):
    python -m scripts.test_retrieval

بيستهلك 3 request من Gemini embedding API (الحالة الثانية بتترفض قبل الـembedding).
الـexit code بيبقى 1 لو أي حالة ماطلعتش زي المتوقع.
"""

import sys
from collections.abc import Callable

from dotenv import load_dotenv

from app.rag.retrieval import PermissionDeniedError, RetrievedChunk, retrieve_chunks

PROPERTY_QUERY = "Is there a fully finished villa with a private garden available?"
PAYMENT_QUERY = "ما هي خطط التقسيط المتاحة ونسبة الدفعة المقدمة؟"
# سؤال عام بس مايل ناحية الوحدات والأسعار عن قصد: لو الفلترة بالـrole اتكسرت،
# chunks من property_listings/payment_policies هتظهر فوق — سؤال "عن الشركة" بس
# كان هيعدّي حتى من غير فلترة.
HR_GENERAL_QUERY = "What units are available, how much do they cost, and how can I contact the company?"


def print_chunks(chunks: list[RetrievedChunk]) -> None:
    for rank, chunk in enumerate(chunks, start=1):
        section = " > ".join(chunk.metadata.section.values()) or "—"
        preview = " ".join(chunk.content.split())[:110]
        print(
            f"  {rank}. [{chunk.similarity_score:.3f}] {chunk.doc_title} "
            f"(v{chunk.metadata.version}) | {section}\n     {preview}…"
        )


def case_sales_property_listings() -> bool:
    """Sales مسموح له بـproperty_listings → لازم يرجع نتايج كلها من نفس الـcategory."""
    chunks = retrieve_chunks(PROPERTY_QUERY, role="sales", category="property_listings")
    print_chunks(chunks)
    return bool(chunks) and all(c.category == "property_listings" for c in chunks)


def case_hr_property_listings_denied() -> bool:
    """HR مش مسموح له بـproperty_listings → لازم PermissionDeniedError، مش نتايج فاضية."""
    try:
        chunks = retrieve_chunks(PROPERTY_QUERY, role="hr", category="property_listings")
    except PermissionDeniedError as exc:
        print(f"  🔒 PermissionDeniedError: {exc}")
        return exc.role == "hr" and exc.category == "property_listings"
    print(f"  ❗ مفيش exception — رجع {len(chunks)} chunk بدل الرفض")
    return False


def case_sales_payment_both_versions() -> bool:
    """النسختين (2025.1 و2026.1) لازم يكونوا قابلين للاسترجاع — حل التضارب مش هنا."""
    chunks = retrieve_chunks(PAYMENT_QUERY, role="sales", category="payment_policies")
    print_chunks(chunks)
    versions = {c.metadata.version for c in chunks}
    print(f"  النسخ اللي ظهرت: {sorted(versions)}")
    return {"2025.1", "2026.1"} <= versions and all(
        c.category == "payment_policies" for c in chunks
    )


def case_hr_no_category_scoped_to_allowed() -> bool:
    """HR من غير category → البحث محصور في company_info_support، مش في كل الداتابيز."""
    chunks = retrieve_chunks(HR_GENERAL_QUERY, role="hr")
    print_chunks(chunks)
    categories = {c.category for c in chunks}
    print(f"  الـcategories اللي ظهرت: {sorted(categories)}")
    # bool(chunks): نتيجة فاضية هتعدّي شرط الـcategory من غير ما تثبت حاجة.
    return bool(chunks) and categories == {"company_info_support"}


CASES: list[tuple[str, Callable[[], bool]]] = [
    ("sales → property_listings (متوقع: نتايج)", case_sales_property_listings),
    ("hr → property_listings (متوقع: رفض)", case_hr_property_listings_denied),
    ("sales → payment_policies (متوقع: النسختين)", case_sales_payment_both_versions),
    ("hr → من غير category (متوقع: company_info_support بس)", case_hr_no_category_scoped_to_allowed),
]


def main() -> None:
    # على Windows، لما الـoutput يتعمله redirect/pipe بيبقى cp1252 وبيقع مع العربي.
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    failed = 0
    for title, case in CASES:
        print(f"\n=== {title} ===")
        passed = case()
        failed += not passed
        print(f"  → {'✅ PASS' if passed else '❌ FAIL'}")

    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
