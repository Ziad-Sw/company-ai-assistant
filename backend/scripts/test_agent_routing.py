"""
اختبار يدوي لـrouting الـagent في /chat على الداتابيز وOpenRouter الحقيقيين (Phase 2).

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.test_agent_routing

بيغطي: التوجيه الصح لكل category (إنجليزي + عربي)، الرفض عبر الـgraph كامل
ووحفظه كرسالة assistant، السؤال العام (decided_category=None → scope الـrole
كامل)، الـmemory على محادثتين في نفس conversation_id، مسار "مش لاقي"،
والـregression (SSE framing / موديل مدفوع / دور غير معروف). كمان فحوصات
deterministic أوفلاين (parse الـcategory وcheck_permission) من غير أي quota.

بيستهلك تقريباً: 21 chat request من الـ50 المجانية في اليوم بتاعة OpenRouter
(كل رد مولّد = 2: تحديد الـcategory + الإجابة؛ الرفض و"مش لاقي" = 1 بس؛
والموديلات المجانية ممكن تضيف retries لو رجّعت رد فاضي)،
و10 Gemini embeddings، وقائمة /models مرة واحدة. الحالات بتتشغل بالترتيب
وكل حالة بتطبع تكلفتها — لو الـquota خلص في النص، اللي عدّى قبل كده باقي
مفهوم من الملخص الآخر. المحادثات اللي بيعملها بتتمسح في الآخر.
الـexit code: 0 لو كله نجح، 1 لو أي حالة فشلت، 2 لو المتطلبات مش جاهزة.
"""

import json
import os
import sys
from collections.abc import Callable
from uuid import UUID

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import ValidationError
from sqlalchemy import text

from app.agent.nodes import check_permission, parse_decided_category
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.llm.prompts import NOT_FOUND_MESSAGE

# موديل محدد ومسمّى للنتايج الـdeterministic — ده للـاختبار بس، وGET /models
# والـdropdown بتاع المستخدمين فاضلين بيجيبوا كل الموديلات المجانية زي ما هما.
CHAT_MODEL = "nvidia/nemotron-3.5-lightning:free"
PAID_MODEL = "openai/gpt-4o"

# أسئلة التوجيه: إنجليزي + عربي لكل category (حالتين 1 و2).
ROUTING_CASES = [
    ("property_listings", "Is there a fully finished villa with a private garden available?",
     "هل فيه فيلا تشطيب كامل بحديقة خاصة متاحة؟"),
    ("payment_policies", "What is the down payment percentage in installment plan A?",
     "ما هي نسبة الدفعة المقدمة في خطة التقسيط A؟"),
    ("company_info_support", "How can I contact customer support after handover?",
     "أقدر أتواصل مع خدمة العملاء إزاي بعد التسليم؟"),
]
# سؤال عام متعدد المواضيع (property + support) — عمداً مايل ناحية category ممنوعة
# على hr، عشان لو الفلترة broken في مسار None هترجع chunks ممنوعة والحالة تفشل
# (نفس فخ case_hr_no_category_scoped_to_allowed في test_retrieval.py).
BROAD_QUESTION = "What units are available, how much do they cost, and how can I contact the company?"
MEMORY_TURN_1 = "What unit types exist in Marina Heights?"
MEMORY_TURN_2 = "How much is the cheapest one?"
NOT_FOUND_QUESTION = "What's the weather like today in Cairo?"

created_conversation_ids: list[str] = []


def find_user_id(role: str) -> UUID | None:
    with get_session_factory().begin() as session:
        return session.execute(
            text("SELECT id FROM public.profiles WHERE role = :role LIMIT 1"), {"role": role}
        ).scalar_one_or_none()


def has_sources_column() -> bool:
    with get_session_factory().begin() as session:
        return session.execute(
            text(
                "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name = 'messages' AND column_name = 'sources'"
            )
        ).scalar_one_or_none() is not None


def env_is_set(name: str) -> bool:
    return bool(os.environ.get(name))


def missing_preconditions(user_ids: dict[str, UUID | None]) -> list[str]:
    problems = [
        f"مفيش موظف role={role} في profiles — اعمل seed للـdemo accounts (docs/demo-accounts.md)"
        for role, user_id in user_ids.items()
        if user_id is None
    ]
    if not has_sources_column():
        problems.append("عمود messages.sources مش موجود — طبّق migrations/001_add_messages_sources.sql")
    for name, label in [
        ("OPENROUTER_API_KEY", "OPENROUTER_API_KEY"),
        ("GEMINI_API_KEY", "GEMINI_API_KEY (embeddings)"),
        ("DATABASE_URL", "DATABASE_URL"),
    ]:
        if not env_is_set(name):
            problems.append(f"{label} فاضي أو مش موجود في backend/.env")
    try:
        get_settings()
    except ValidationError:
        problems.append("OPENROUTER_API_KEY مش صالح في backend/.env")
    return problems


def parse_sse(body: str) -> list[tuple[str, dict]]:
    """'event: x\\ndata: {...}\\n\\n' → [(x, {...})] — البيانات لازم JSON سطر واحد (الـframing)."""
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((fields["event"], json.loads(fields["data"])))
    return events


def post_chat(client: TestClient, body: dict) -> Response:
    response = client.post("/chat", json=body)
    if conversation_id := response.headers.get("x-conversation-id"):
        created_conversation_ids.append(conversation_id)
    return response


def chat_body(user_id: UUID, message: str, role: str = "sales", model: str = CHAT_MODEL) -> dict:
    return {"message": message, "role": role, "user_id": str(user_id), "model": model}


def stored_messages(client: TestClient, conversation_id: str, user_id: UUID) -> list[dict]:
    response = client.get(f"/conversations/{conversation_id}", params={"user_id": str(user_id)})
    response.raise_for_status()
    return response.json()["messages"]


def source_categories(client: TestClient, conversation_id: str, user_id: UUID) -> list[str]:
    """categories المستندات اللي المصادر المحفوظة بتشاور عليها — من chunk_id → documents."""
    chunk_ids = [
        source["chunk_id"]
        for message in stored_messages(client, conversation_id, user_id)
        if message["role"] == "assistant"
        for source in message["sources"]
    ]
    with get_session_factory().begin() as session:
        return sorted(
            session.execute(
                text(
                    "SELECT DISTINCT d.category FROM public.chunks AS c "
                    "JOIN public.documents AS d ON d.id = c.document_id WHERE c.id = ANY(:ids)"
                ),
                {"ids": chunk_ids},
            ).scalars()
        )


def assert_well_formed_sse(response: Response) -> list[tuple[str, dict]]:
    """content-type وframing الصح شرط في كل حالة — هنا مكان التجميع الواحد."""
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


def events_summary(events: list[tuple[str, dict]]) -> str:
    """أسماء الـevents + رسايل error/denied — عشان فشل الموديل يبان من أول نظرة."""
    parts = []
    for name, payload in events:
        if name in ("error", "denied"):
            parts.append(f"{name}: {payload.get('message', payload)!r}")
        else:
            parts.append(name)
    return " + ".join(parts)


def case_offline_deterministic_contracts() -> bool:
    """فحوصات الـnodes الـdeterministic من غير LLM ولا DB ولا quota — قرار معتمد:
    الـcategory المختلقة مش رفض (fallback لـNone)، والمعروفة المش مسموحة = رفض."""
    checks = [
        parse_decided_category("property_listings") == "property_listings",
        parse_decided_category("  payment_policies.\n") == "payment_policies",
        parse_decided_category("none") is None,
        parse_decided_category("Answer: company_info_support") == "company_info_support",
        parse_decided_category("villa_specs") is None,
        parse_decided_category("") is None,
        check_permission({"role": "hr", "decided_category": "property_listings"})["permission_result"] == "denied",
        check_permission({"role": "hr", "decided_category": "villa_specs"})
        == {"decided_category": None, "permission_result": "allowed", "denial_message": None},
        check_permission({"role": "sales", "decided_category": "payment_policies"})["permission_result"] == "allowed",
    ]
    for index, passed in enumerate(checks):
        if not passed:
            print(f"  الفحص رقم {index} فشل")
    return all(checks)


def _assert_routes_to_expected(client: TestClient, user_id: UUID, question: str, expected_category: str) -> bool:
    """سؤال واحد واضح → مصادر المحادثة كلها من الـcategory المتوقعة (على saved sources)."""
    response = post_chat(client, chat_body(user_id, question))
    print(f"  [{expected_category}] status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    if events[-1][0] != "done":
        print(f"  آخر event مش done: {events_summary(events)}")
        return False
    categories = source_categories(client, response.headers["x-conversation-id"], user_id)
    print(f"  categories المصادر: {categories}")
    return categories == [expected_category]


def case_routes_each_category_in_english(client: TestClient, user_id: UUID) -> bool:
    """لكل category سؤال إنجليزي واضح → التوجيه الصح."""
    return all(
        _assert_routes_to_expected(client, user_id, english, expected_category)
        for expected_category, english, _ in ROUTING_CASES
    )


def case_routes_each_category_in_arabic(client: TestClient, user_id: UUID) -> bool:
    """لكل category سؤال عربي واضح → التوجيه الصح (دعم اللغتين)."""
    return all(
        _assert_routes_to_expected(client, user_id, arabic, expected_category)
        for expected_category, _, arabic in ROUTING_CASES
    )


def case_hr_denial_saved(client: TestClient, user_id: UUID) -> bool:
    """HR + سؤال واضح إنه property_listings → denied، والرفض محفوظ كرسالة assistant
    بنص رسالة الرفض اللي ظهرت بالظبط ومصادرها فاضية (قرار معتمد في Phase 2)."""
    response = post_chat(client, chat_body(user_id, ROUTING_CASES[0][1], role="hr"))
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    print(f"  events: {events_summary(events)}")
    if [name for name, _ in events] != ["denied"]:
        return False
    denial_message = events[0][1]["message"]
    print(f"  رسالة الرفض: {denial_message}")
    messages = stored_messages(client, response.headers["x-conversation-id"], user_id)
    print(f"  الرسايل المحفوظة: {[m['role'] for m in messages]}")
    return (
        [m["role"] for m in messages] == ["user", "assistant"]
        and messages[1]["content"] == denial_message
        and messages[1]["sources"] == []
    )


def case_sales_broad_spans_allowed_scope(client: TestClient, user_id: UUID) -> bool:
    """سؤال عام متعدد المواضيع (sales) → scope كامل: مصادر من أكتر من category
    مسموحة. لو الـagent وَجّه لـcategory واحدة بثقة، الحالة تفشل بالتصميم —
    ده اختبار مسار None/الفشل-الآمن مش اختبار routing."""
    response = post_chat(client, chat_body(user_id, BROAD_QUESTION))
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    if events[-1][0] != "done":
        print(f"  آخر event مش done: {events_summary(events)}")
        return False
    categories = source_categories(client, response.headers["x-conversation-id"], user_id)
    print(f"  categories المصادر: {categories} (المسموح لـsales: الثلاثة كلهم)")
    return len(categories) >= 2


def case_hr_broad_scoped_to_support_only(client: TestClient, user_id: UUID) -> bool:
    """نفس السؤال العام مع hr → مصادر من company_info_support بس. الرفض هنا
    (routing لـcategory ممنوعة بدل none) بيفشل الحالة برسالة واضحة."""
    response = post_chat(client, chat_body(user_id, BROAD_QUESTION, role="hr"))
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    if events[-1][0] != "done":
        print(f"  المتوقع done ومصادر من company_info_support، طلع: {events_summary(events)}")
        return False
    categories = source_categories(client, response.headers["x-conversation-id"], user_id)
    print(f"  categories المصادر: {categories} (المسموح لـhr: company_info_support بس)")
    return categories == ["company_info_support"]


def case_memory_two_turns(client: TestClient, user_id: UUID) -> bool:
    """دورين في نفس المحادثة: السؤال التاني بـreference ("الأرخص واحدة؟") من غير
    ما يعيد اسم الـcompound. العقد المتحقق منه هنا: الدور التاني بيجاوب من غير
    error وبمصادر مش فاضية من الـcategories المسموحة لـsales، والدورين اتحفظوا
    في نفس المحادثة (4 رسايل). **دقة توجيه سؤال الضمير نفسها** (هل sources كلها
    listings؟) دي جودة موديل — بيتقاس في golden dataset بتاع RAGAS في Phase 4،
    مش في اختبار endpoint (نفس مبدأ مافيش assertion على صياغة الرد)."""
    first = post_chat(client, chat_body(user_id, MEMORY_TURN_1))
    print(f"  الدور الأول: status={first.status_code}")
    if first.status_code != 200:
        return False
    events = assert_well_formed_sse(first)
    if events[-1][0] != "done":
        print(f"  الدور الأول ماخدش done: {events_summary(events)}")
        return False
    conversation_id = first.headers["x-conversation-id"]
    second = post_chat(client, {**chat_body(user_id, MEMORY_TURN_2), "conversation_id": conversation_id})
    print(f"  الدور التاني: status={second.status_code}")
    if second.status_code != 200:
        print(f"  {second.text}")
        return False
    events = assert_well_formed_sse(second)
    if events[-1][0] != "done":
        print(f"  الدور التاني ماخدش done: {events_summary(events)}")
        return False
    categories = source_categories(client, conversation_id, user_id)
    messages = stored_messages(client, conversation_id, user_id)
    print(f"  categories مصادر الدورين: {categories} (المسموح لـsales: الثلاثة كلهم) | الرسايل: {[m['role'] for m in messages]}")
    return (
        bool(categories)
        and set(categories) <= {"property_listings", "payment_policies", "company_info_support"}
        and [m["role"] for m in messages] == ["user", "assistant"] * 2
    )


def case_not_found_canned_and_saved(client: TestClient, user_id: UUID) -> bool:
    """سؤال ملوش علاقة بالبيانات → الرد الجاهز بالنص، sources=[]، ومحفوظ كرد assistant."""
    response = post_chat(client, chat_body(user_id, NOT_FOUND_QUESTION))
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    tokens = [payload["text"] for name, payload in events if name == "token"]
    answer = "".join(tokens)
    print(f"  events: {len(tokens)} token + {[name for name, _ in events if name != 'token']}")
    if [name for name, _ in events] != ["token", "done"]:
        return False
    messages = stored_messages(client, response.headers["x-conversation-id"], user_id)
    print(f"  الرسايل المحفوظة: {[m['role'] for m in messages]}")
    return (
        answer == NOT_FOUND_MESSAGE
        and events[-1][1]["sources"] == []
        and [m["role"] for m in messages] == ["user", "assistant"]
        and messages[1]["content"] == NOT_FOUND_MESSAGE
        and messages[1]["sources"] == []
    )


def case_regressions_no_llm_cost(client: TestClient, user_id: UUID) -> bool:
    """موديل مدفوع → 422، ودور غير معروف → 422 — قبل أي كتابة (مفيش تكلفة LLM)."""
    before = client.get("/conversations", params={"user_id": str(user_id)}).json()
    paid = client.post("/chat", json={**chat_body(user_id, BROAD_QUESTION), "model": PAID_MODEL})
    unknown = client.post("/chat", json=chat_body(user_id, BROAD_QUESTION, role="guest"))
    after = client.get("/conversations", params={"user_id": str(user_id)}).json()
    print(f"  موديل مدفوع: {paid.status_code} (متوقع 422) | دور غير معروف: {unknown.status_code} (متوقع 422)")
    print(f"  عدد المحادثات قبل/بعد: {len(before)}/{len(after)}")
    return paid.status_code == 422 and unknown.status_code == 422 and before == after


def delete_created_conversations() -> None:
    # messages بتتمسح معاها (on delete cascade).
    with get_session_factory().begin() as session:
        for conversation_id in created_conversation_ids:
            session.execute(
                text("DELETE FROM public.conversations WHERE id = :id"), {"id": conversation_id}
            )


def run_cases(client: TestClient, user_ids: dict[str, UUID]) -> int:
    """(العنوان، الحالة، تكلفة LLM التقديرية) — بالترتيب، والفشل مابيقفلش اللي بعده."""
    cases: list[tuple[str, Callable[[], bool], int]] = [
        ("فحوصات deterministic أوفلاين (تكلفة: 0)", case_offline_deterministic_contracts, 0),
        ("توجيه كل category — إنجليزي (تكلفة: 6 LLM)", lambda: case_routes_each_category_in_english(client, user_ids["sales"]), 6),
        ("توجيه كل category — عربي (تكلفة: 6 LLM)", lambda: case_routes_each_category_in_arabic(client, user_ids["sales"]), 6),
        ("hr → سؤال property_listings (متوقع: denied + حفظ الرفض) (تكلفة: 1 LLM)",
         lambda: case_hr_denial_saved(client, user_ids["hr"]), 1),
        ("sales → سؤال عام متعدد المواضيع (متوقع: أكتر من category مسموحة) (تكلفة: 2 LLM)",
         lambda: case_sales_broad_spans_allowed_scope(client, user_ids["sales"]), 2),
        ("hr → نفس السؤال العام (متوقع: company_info_support بس) (تكلفة: 1 LLM)",
         lambda: case_hr_broad_scoped_to_support_only(client, user_ids["hr"]), 1),
        ("memory — دورين في نفس المحادثة (تكلفة: 4 LLM)", lambda: case_memory_two_turns(client, user_ids["sales"]), 4),
        ("سؤال ملوش علاقة (متوقع: الرد الجاهز + حفظه) (تكلفة: 1 LLM)",
         lambda: case_not_found_canned_and_saved(client, user_ids["sales"]), 1),
        ("regression — موديل مدفوع ودور غير معروف (تكلفة: 0)",
         lambda: case_regressions_no_llm_cost(client, user_ids["sales"]), 0),
    ]
    failed = 0
    for title, case, llm_cost in cases:
        print(f"\n=== {title} ===")
        try:
            passed = case()
        except Exception as exc:
            print(f"  استثناء غير متوقع: {exc!r}")
            passed = False
        failed += not passed
        print(f"  → {'✅ PASS' if passed else '❌ FAIL'}")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return failed


def main() -> None:
    # على Windows، لما الـoutput يتعمله redirect/pipe بيبقى cp1252 وبيقع مع العربي.
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    user_ids = {role: find_user_id(role) for role in ("sales", "hr")}
    if problems := missing_preconditions(user_ids):
        print("المتطلبات مش جاهزة:\n" + "\n".join(f"  - {p}" for p in problems))
        sys.exit(2)

    # import هنا مش فوق: app.main بيعمل fail fast لو OPENROUTER_API_KEY ناقص،
    # وعايزين رسالة المتطلبات اللي فوق تظهر الأول بدل traceback.
    from app.main import app

    # with: portal واحد لكل الحالات (نفس الـevent loop) — الـAsyncOpenAI client
    # الـcached بيعيد استخدام connections من نفس الـloop؛ من غير with كل request
    # بياخد loop جديد، والاتصال من الـloop المقفول بيقع بـ"Event loop is closed".
    with TestClient(app) as client:
        try:
            failed = run_cases(client, user_ids)
        finally:
            delete_created_conversations()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
