"""
سكريبت قياس لمرة واحدة (throwaway diagnostic): توزيع درجات التشابه الفعلية
قبل ما نقرر similarity threshold للاسترجاع (مفيش threshold في retrieval.py دلوقتي).

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.measure_similarity

بيشغّل retrieve_chunks(role="admin") — كل الـcategories متاحة — لكل سؤال
بـtop_k=5، ويطبع score كل chunk. بيستهلك request من Gemini embedding لكل سؤال
(11 سؤال). السكريبت ده diagnostic للاستكشاف بس — مش جزء دائم من التطبيق،
ومفيش أي قرارات threshold هنا؛ دي مسؤولية القرار اللي بيتاخد بعد القياس.

الـexit code: 0 دايماً (بالتجربة والاستكشاف).
"""

import sys

from dotenv import load_dotenv

from app.rag.retrieval import retrieve_chunks

load_dotenv()

# on-topic: صياغات واقعية من محتوى data/raw الفعلي (واحد لكل category على الأقل).
# borderline: قريبة من الدومين بس مش مغطاة في البيانات (إيجار/تمويل/تجاري).
# off-topic: ملهاش أي علاقة بشركة عقارية — category=None زي الـagent اللي محددش.
QUERY_GROUPS: list[tuple[str, str, str]] = [
    # (المجموعة، category المطلوب البحث فيها (None = الكل)، السؤال)
    ("on-topic", "property_listings", "Looking for a 3-bedroom apartment in Marina Heights New Cairo — what's available and at what price?"),
    ("on-topic", "property_listings", "هل يوجد فيلا بالتشطيب الكامل في ماونتن فيو أكتوبر وكم سعرها؟"),
    ("on-topic", "payment_policies", "إيه نسبة الدفعة المقدمة في خطة التقسيط A وعدد سنوات التقسيط؟"),
    ("on-topic", "company_info_support", "How do I submit a maintenance request after delivery, and what are the support hotline working hours?"),
    ("off-topic", None, "What's the weather forecast for tomorrow in Miami?"),
    ("off-topic", None, "What's the best way to cook pasta carbonara?"),
    ("off-topic", None, "Who won the Champions League final last night?"),
    ("off-topic", None, "Tell me something interesting about penguins."),
    ("borderline", "property_listings", "Can I rent or lease an apartment instead of buying it?"),
    ("borderline", "payment_policies", "Does Reel Estate provide mortgage financing through a bank, and what are the interest rates?"),
    ("borderline", "property_listings", "Are there any commercial offices or shops for sale?"),
]

TITLE_MAX_CHARS = 40
QUERY_MAX_CHARS = 55


def print_table(group: str, rows: list[tuple[str, str, int, float, str]]) -> None:
    print(f"\n=== {group.upper()} ===")
    header = f"{'QUERY':{QUERY_MAX_CHARS}} | {'CAT':21s} | {'#':>1s} | {'SCORE':>6s} | DOC_TITLE"
    print(header)
    print("-" * len(header))
    for query, category, rank, score, title in rows:
        short_query = query[:QUERY_MAX_CHARS].ljust(QUERY_MAX_CHARS)
        short_cat = (category or "(all)").ljust(21)
        short_title = title[:TITLE_MAX_CHARS]
        print(f"{short_query} | {short_cat} | {rank} | {score:>6.4f} | {short_title}")
    scores = [score for _, _, _, score, _ in rows]
    print(f"  → top-1 range: {max(scores):.4f} | min returned: {min(scores):.4f}")


def main() -> None:
    # على Windows، لما الـoutput يتعمله redirect/pipe بيبقى cp1252 وبيقع مع العربي.
    sys.stdout.reconfigure(encoding="utf-8")

    for group in ("on-topic", "off-topic", "borderline"):
        rows = []
        for query_group, category, query in QUERY_GROUPS:
            if query_group != group:
                continue
            chunks = retrieve_chunks(query, role="admin", category=category, top_k=5)
            rows.extend(
                (query, category, rank, chunk.similarity_score, chunk.doc_title)
                for rank, chunk in enumerate(chunks, start=1)
            )
        print_table(group, rows)


if __name__ == "__main__":
    main()
