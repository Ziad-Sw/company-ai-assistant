"""
تشخيص مؤقت (مش production code): هل prompt الـrespond لحالة hr_broad أكبر/أصعب
بنيوياً من الحالات اللي بتعدّي؟

بنسترجع الـchunks فعلياً (retrieve_chunks — Postgres + Gemini embeddings فقط،
**صفر OpenRouter requests**) ونبني الـsystem prompt اللي respond بيبعته فعلاً
(build_grounded_system_prompt)، ونقارن hr_broad بحالات PASSING جنب بعض:
عدد الـchunks، عدد الـcategories/المستندات، الدرجات، الحجم بالحروف وتقدير
الـtokens، وتكرار/تقارب الـchunks (near-duplicates بـdifflib).

طريقة التشغيل (من backend/ والـvenv مفعّلة):
    python -m scripts.diagnose_hr_broad_prompt
"""

import difflib
import io
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

from app.agent.nodes import TOP_K
from app.llm.prompts import build_grounded_system_prompt
from app.rag.retrieval import retrieve_chunks

# السؤال verbatim من test_agent_routing.py (English).
BROAD_QUESTION = "What units are available, how much do they cost, and how can I contact the company?"

# حالات المقارنة: (الاسم، السؤال، role، decided_category، history اللي هيوصل لـrespond)
CASES = [
    ("hr_broad (FAIL)", BROAD_QUESTION, "hr", None, []),
    ("sales_broad (PASS)", BROAD_QUESTION, "sales", None, []),
    ("memory_turn1 (PASS)", "What unit types exist in Marina Heights?", "sales", None, []),
    ("support_en (PASS)", "How can I contact customer support after handover?", "sales", "company_info_support", []),
    ("support_ar (PASS)", "أقدر أتواصل مع خدمة العملاء إزاي بعد التسليم؟", "hr", "company_info_support", []),
    ("memory_turn2 (PASS)", "How much is the cheapest one?", "sales", None, [
        {"role": "user", "content": "What unit types exist in Marina Heights?"},
        {"role": "assistant", "content": "Marina Heights offers apartments, duplexes, and villas."},
    ]),
]


def rough_tokens(text: str) -> int:
    return len(text) // 4


def near_duplicate_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def main() -> None:
    load_dotenv()
    print(f"top_k = {TOP_K}\n")

    for name, question, role, category, history in CASES:
        chunks = retrieve_chunks(query=question, role=role, category=category, top_k=TOP_K)
        system_prompt = build_grounded_system_prompt(chunks)
        user_turn = question
        answer_messages_total = len(system_prompt) + sum(len(m["content"]) for m in history) + len(user_turn)

        titles = Counter(chunk.doc_title for chunk in chunks)
        categories = sorted({chunk.category for chunk in chunks})
        contents = [chunk.content for chunk in chunks]

        max_pair_ratio = 0.0
        max_pair = None
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                ratio = near_duplicate_ratio(contents[i], contents[j])
                if ratio > max_pair_ratio:
                    max_pair_ratio, max_pair = ratio, (i, j)

        print(f"=== {name} ===")
        print(f"  السؤال verbatim: {question!r}")
        print(f"  chunks: {len(chunks)} | categories: {categories} | مستندات مميزة: {len(titles)}")
        print(f"  تكرار المستندات: {dict(titles)}")
        print(f"  درجات التشابه: {[round(chunk.similarity_score, 4) for chunk in chunks]}")
        print(f"  طول كل chunk (حروف): {[len(content) for content in contents]}")
        print(f"  system prompt: {len(system_prompt)} حرف (~{rough_tokens(system_prompt)} token تقديري)")
        print(f"  رسايل respond كاملة (system + history {len(history)} + user): "
              f"{answer_messages_total} حرف (~{rough_tokens('x' * answer_messages_total)} token تقديري)")
        if max_pair:
            print(f"  أعلى تشابه بين chunkين: {max_pair_ratio:.3f} (chunks {max_pair})")
        print()

    print("ملاحظة: الإجابات المباشرة من التشغيل الحي للأمس (usage من OpenRouter): "
          "hr_broad answer prompt_tokens=974 | memory_turn1 answer prompt_tokens=999 "
          "| memory_turn2 answer prompt_tokens=1136-1146")


if __name__ == "__main__":
    main()
