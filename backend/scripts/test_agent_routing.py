"""
اختبار يدوي لـrouting الـagent في /chat على الداتابيز وOpenRouter الحقيقيين (Phase 2).

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.test_agent_routing
    python -m scripts.test_agent_routing --only memory,hr_broad   (subset معين — للـreruns المقيدة بالـquota؛ بدون flag بيشتغل الكل)

بيغطي: التوجيه الصح لكل category (إنجليزي + عربي)، الرفض عبر الـgraph كامل
ووحفظه كرسالة assistant، السؤال العام (decided_category=None → scope الـrole
كامل)، الـmemory على محادثتين في نفس conversation_id، مسار "مش لاقي"،
والـregressions (SSE framing / موديل مدفوع / نداء من غير Authorization → 401).
كمان فحوصات deterministic أوفلاين (parse الـcategory وcheck_permission) من
غير أي quota.

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

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import ValidationError
from sqlalchemy import text

from app.agent.nodes import check_permission, parse_decided_category
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.llm.prompts import NOT_FOUND_MESSAGE
from scripts.demo_auth import login_all

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


def missing_preconditions() -> list[str]:
    problems = []
    if not has_sources_column():
        problems.append("عمود messages.sources مش موجود — طبّق migrations/001_add_messages_sources.sql")
    for name, label in [
        ("OPENROUTER_API_KEY", "OPENROUTER_API_KEY"),
        ("GEMINI_API_KEY", "GEMINI_API_KEY (embeddings)"),
        ("DATABASE_URL", "DATABASE_URL"),
        ("SUPABASE_URL", "SUPABASE_URL (تسجيل دخول الـdemo accounts)"),
        ("SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY (تسجيل دخول الـdemo accounts)"),
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


def post_chat(client: TestClient, token: str, body: dict) -> Response:
    response = client.post("/chat", json=body, headers={"Authorization": f"Bearer {token}"})
    if conversation_id := response.headers.get("x-conversation-id"):
        created_conversation_ids.append(conversation_id)
    return response


def chat_body(message: str, model: str = CHAT_MODEL) -> dict:
    # مفيش role ولا user_id في الـbody: بيتقروا من الـJWT على السيرفر
    # (app/auth/dependencies.py) — الدور بيتحدد بحساب الـdemo اللي اتعمل بيه login.
    return {"message": message, "model": model}


def stored_messages(client: TestClient, conversation_id: str, token: str) -> list[dict]:
    response = client.get(f"/conversations/{conversation_id}", headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    return response.json()["messages"]


def source_categories(client: TestClient, conversation_id: str, token: str) -> list[str]:
    """categories المستندات اللي المصادر المحفوظة بتشاور عليها — من chunk_id → documents."""
    chunk_ids = [
        source["chunk_id"]
        for message in stored_messages(client, conversation_id, token)
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


def _assert_routes_to_expected(client: TestClient, token: str, question: str, expected_category: str) -> bool:
    """سؤال واحد واضح → مصادر المحادثة كلها من الـcategory المتوقعة (على saved sources)."""
    response = post_chat(client, token, chat_body(question))
    print(f"  [{expected_category}] status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    if events[-1][0] != "done":
        print(f"  آخر event مش done: {events_summary(events)}")
        return False
    categories = source_categories(client, response.headers["x-conversation-id"], token)
    print(f"  categories المصادر: {categories}")
    return categories == [expected_category]


def case_routes_each_category_in_english(client: TestClient, token: str) -> bool:
    """لكل category سؤال إنجليزي واضح → التوجيه الصح."""
    return all(
        _assert_routes_to_expected(client, token, english, expected_category)
        for expected_category, english, _ in ROUTING_CASES
    )


def case_routes_each_category_in_arabic(client: TestClient, token: str) -> bool:
    """لكل category سؤال عربي واضح → التوجيه الصح (دعم اللغتين)."""
    return all(
        _assert_routes_to_expected(client, token, arabic, expected_category)
        for expected_category, _, arabic in ROUTING_CASES
    )


def case_hr_denial_saved(client: TestClient, token: str) -> bool:
    """HR + سؤال واضح إنه property_listings → denied، والرفض محفوظ كرسالة assistant
    بنص رسالة الرفض اللي ظهرت بالظبط ومصادرها فاضية (قرار معتمد في Phase 2)."""
    response = post_chat(client, token, chat_body(ROUTING_CASES[0][1]))
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
    messages = stored_messages(client, response.headers["x-conversation-id"], token)
    print(f"  الرسايل المحفوظة: {[m['role'] for m in messages]}")
    return (
        [m["role"] for m in messages] == ["user", "assistant"]
        and messages[1]["content"] == denial_message
        and messages[1]["sources"] == []
    )


def case_sales_broad_spans_allowed_scope(client: TestClient, token: str) -> bool:
    """سؤال عام متعدد المواضيع (sales) → scope كامل: مصادر من أكتر من category
    مسموحة. لو الـagent وَجّه لـcategory واحدة بثقة، الحالة تفشل بالتصميم —
    ده اختبار مسار None/الفشل-الآمن مش اختبار routing."""
    response = post_chat(client, token, chat_body(BROAD_QUESTION))
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    if events[-1][0] != "done":
        print(f"  آخر event مش done: {events_summary(events)}")
        return False
    categories = source_categories(client, response.headers["x-conversation-id"], token)
    print(f"  categories المصادر: {categories} (المسموح لـsales: الثلاثة كلهم)")
    return len(categories) >= 2


def case_hr_broad_scoped_to_support_only(client: TestClient, token: str) -> bool:
    """نفس السؤال العام مع hr → مصادر من company_info_support بس. الرفض هنا
    (routing لـcategory ممنوعة بدل none) بيفشل الحالة برسالة واضحة."""
    response = post_chat(client, token, chat_body(BROAD_QUESTION))
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = assert_well_formed_sse(response)
    if events[-1][0] != "done":
        print(f"  المتوقع done ومصادر من company_info_support، طلع: {events_summary(events)}")
        return False
    categories = source_categories(client, response.headers["x-conversation-id"], token)
    print(f"  categories المصادر: {categories} (المسموح لـhr: company_info_support بس)")
    return categories == ["company_info_support"]


def case_memory_two_turns(client: TestClient, token: str) -> bool:
    """دورين في نفس المحادثة: السؤال التاني بـreference ("الأرخص واحدة؟") من غير
    ما يعيد اسم الـcompound. العقد المتحقق منه هنا: الدور التاني بيجاوب من غير
    error وبمصادر مش فاضية من الـcategories المسموحة لـsales، والدورين اتحفظوا
    في نفس المحادثة (4 رسايل). **دقة توجيه سؤال الضمير نفسها** (هل sources كلها
    listings؟) دي جودة موديل — بيتقاس في golden dataset بتاع RAGAS في Phase 4،
    مش في اختبار endpoint (نفس مبدأ مافيش assertion على صياغة الرد)."""
    first = post_chat(client, token, chat_body(MEMORY_TURN_1))
    print(f"  الدور الأول: status={first.status_code}")
    if first.status_code != 200:
        return False
    events = assert_well_formed_sse(first)
    if events[-1][0] != "done":
        print(f"  الدور الأول ماخدش done: {events_summary(events)}")
        return False
    conversation_id = first.headers["x-conversation-id"]
    second = post_chat(client, token, {**chat_body(MEMORY_TURN_2), "conversation_id": conversation_id})
    print(f"  الدور التاني: status={second.status_code}")
    if second.status_code != 200:
        print(f"  {second.text}")
        return False
    events = assert_well_formed_sse(second)
    if events[-1][0] != "done":
        print(f"  الدور التاني ماخدش done: {events_summary(events)}")
        return False
    categories = source_categories(client, conversation_id, token)
    messages = stored_messages(client, conversation_id, token)
    print(f"  categories مصادر الدورين: {categories} (المسموح لـsales: الثلاثة كلهم) | الرسايل: {[m['role'] for m in messages]}")
    return (
        bool(categories)
        and set(categories) <= {"property_listings", "payment_policies", "company_info_support"}
        and [m["role"] for m in messages] == ["user", "assistant"] * 2
    )


def case_not_found_canned_and_saved(client: TestClient, token: str) -> bool:
    """سؤال ملوش علاقة بالبيانات → الرد الجاهز بالنص، sources=[]، ومحفوظ كرد assistant."""
    response = post_chat(client, token, chat_body(NOT_FOUND_QUESTION))
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
    messages = stored_messages(client, response.headers["x-conversation-id"], token)
    print(f"  الرسايل المحفوظة: {[m['role'] for m in messages]}")
    return (
        answer == NOT_FOUND_MESSAGE
        and events[-1][1]["sources"] == []
        and [m["role"] for m in messages] == ["user", "assistant"]
        and messages[1]["content"] == NOT_FOUND_MESSAGE
        and messages[1]["sources"] == []
    )


def case_regressions_no_llm_cost(client: TestClient, token: str) -> bool:
    """موديل مدفوع → 422، ونداء /chat من غير Authorization → 401 — قبل أي كتابة
    (مفيش تكلفة LLM). (فحص "دور غير معروف → 422" اتشال: الـrole بقى بيتقرا من
    الـJWT على السيرفر ومش حقول request خالص.)"""
    before = client.get("/conversations", headers={"Authorization": f"Bearer {token}"}).json()
    paid = client.post("/chat", json={**chat_body(BROAD_QUESTION), "model": PAID_MODEL},
                       headers={"Authorization": f"Bearer {token}"})
    unauthenticated = client.post("/chat", json=chat_body(BROAD_QUESTION))
    after = client.get("/conversations", headers={"Authorization": f"Bearer {token}"}).json()
    print(
        f"  موديل مدفوع: {paid.status_code} (متوقع 422) | بدون Authorization: "
        f"{unauthenticated.status_code} (متوقع 401)"
    )
    print(f"  عدد المحادثات قبل/بعد: {len(before)}/{len(after)}")
    return paid.status_code == 422 and unauthenticated.status_code == 401 and before == after


def delete_created_conversations() -> None:
    # messages بتتمسح معاها (on delete cascade).
    with get_session_factory().begin() as session:
        for conversation_id in created_conversation_ids:
            session.execute(
                text("DELETE FROM public.conversations WHERE id = :id"), {"id": conversation_id}
            )


def run_cases(client: TestClient, tokens: dict[str, str], only: set[str] | None = None) -> int:
    """(الاسم، العنوان، الحالة، تكلفة LLM التقديرية) — بالترتيب، والفشل مابيقفلش اللي بعده.
    only: أسماء حالات محددة (مفصولة بفواصل عبر --only) لتشغيل subset — useful لو الـquota محدود."""
    cases: list[tuple[str, str, Callable[[], bool], int]] = [
        ("offline", "فحوصات deterministic أوفلاين (تكلفة: 0)", case_offline_deterministic_contracts, 0),
        ("routes_english", "توجيه كل category — إنجليزي (تكلفة: 6 LLM)", lambda: case_routes_each_category_in_english(client, tokens["sales"]), 6),
        ("routes_arabic", "توجيه كل category — عربي (تكلفة: 6 LLM)", lambda: case_routes_each_category_in_arabic(client, tokens["sales"]), 6),
        ("hr_denial", "hr → سؤال property_listings (متوقع: denied + حفظ الرفض) (تكلفة: 1 LLM)",
         lambda: case_hr_denial_saved(client, tokens["hr"]), 1),
        ("sales_broad", "sales → سؤال عام متعدد المواضيع (متوقع: أكتر من category مسموحة) (تكلفة: 2 LLM)",
         lambda: case_sales_broad_spans_allowed_scope(client, tokens["sales"]), 2),
        ("hr_broad", "hr → نفس السؤال العام (متوقع: company_info_support بس) (تكلفة: 1 LLM)",
         lambda: case_hr_broad_scoped_to_support_only(client, tokens["hr"]), 1),
        ("memory", "memory — دورين في نفس المحادثة (تكلفة: 4 LLM)", lambda: case_memory_two_turns(client, tokens["sales"]), 4),
        ("not_found", "سؤال ملوش علاقة (متوقع: الرد الجاهز + حفظه) (تكلفة: 1 LLM)",
         lambda: case_not_found_canned_and_saved(client, tokens["sales"]), 1),
        ("regressions", "regression — موديل مدفوع ونداء بدون Authorization (تكلفة: 0)",
         lambda: case_regressions_no_llm_cost(client, tokens["sales"]), 0),
    ]
    if only is not None:
        known = {name for name, *_ in cases}
        if unknown := only - known:
            print(f"أسماء حالات مش معروفة في --only: {sorted(unknown)} | المعروفة: {sorted(known)}")
            sys.exit(2)
        cases = [case for case in cases if case[0] in only]
    failed = 0
    for name, title, case, _llm_cost in cases:
        print(f"\n=== {title} [{name}] ===")
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
    import argparse

    parser = argparse.ArgumentParser(description="اختبار routing الـagent — يمكن تشغيل subset عبر --only")
    parser.add_argument(
        "--only",
        help="أسماء الحالات المطلوب تشغيلها فقط (مفصولة بفواصل)، مثل: --only memory,hr_broad",
    )
    args = parser.parse_args()
    only = {name.strip() for name in args.only.split(",") if name.strip()} if args.only else None
    # على Windows، لما الـoutput يتعمله redirect/pipe بيبقى cp1252 وبيقع مع العربي.
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    if problems := missing_preconditions():
        print("المتطلبات مش جاهزة:\n" + "\n".join(f"  - {p}" for p in problems))
        sys.exit(2)
    try:
        tokens = login_all(("sales", "hr"))
    except RuntimeError as exc:
        print("المتطلبات مش جاهزة:\n  - " + str(exc))
        sys.exit(2)

    # import هنا مش فوق: app.main بيعمل fail fast لو OPENROUTER_API_KEY ناقص،
    # وعايزين رسالة المتطلبات اللي فوق تظهر الأول بدل traceback.
    from app.main import app

    # with: portal واحد لكل الحالات (نفس الـevent loop) — الـAsyncOpenAI client
    # الـcached بيعيد استخدام connections من نفس الـloop؛ من غير with كل request
    # بياخد loop جديد، والاتصال من الـloop المقفول بيقع بـ"Event loop is closed".
    with TestClient(app) as client:
        try:
            failed = run_cases(client, tokens, only)
        finally:
            delete_created_conversations()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
