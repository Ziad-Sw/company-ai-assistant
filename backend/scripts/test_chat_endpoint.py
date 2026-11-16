"""
اختبار يدوي لـ/chat و/models و/conversations على الداتابيز وOpenRouter الحقيقيين.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.test_chat_endpoint

محتاج قبل التشغيل (السكريبت بيتأكد منهم الأول ويقولك الناقص):
  - OPENROUTER_API_KEY وDATABASE_URL وGEMINI_API_KEY وSUPABASE_URL وSUPABASE_ANON_KEY في الـ.env
  - migrations/001_add_messages_sources.sql متطبّقة
  - حسابات الـdemo (sales وhr) قابلة لتسجيل الدخول في Supabase Auth (docs/demo-accounts.md)

بيستهلك: 1 request من Gemini embedding لكل نداء /chat، ونداءات chat من الـ50
المجانية في اليوم بتاعة OpenRouter (الرد المولّد = 2: تحديد الـcategory + الإجابة،
والرفض = 1: تحديد الـcategory بس)، وقائمة /models بتتجلب من OpenRouter مرة واحدة
(بتتخزن in-memory بـ5 دقايق). المحادثات اللي بيعملها بتتمسح في الآخر.
الـexit code: 0 لو كله نجح، 1 لو أي حالة فشلت، 2 لو المتطلبات مش جاهزة.
"""

import json
import sys
from collections.abc import Callable

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from scripts.demo_auth import login_all

# موديل محدد ومسمّى مش الـauto-router (openrouter/free): الـrouter بيختار موديل
# عشوائي وممكن يرجّع رد فاضي أو rate limit، فالاختبار بيبقى غير deterministic.
CHAT_MODEL = "nvidia/nemotron-3.5-lightning:free"
PAID_MODEL = "openai/gpt-4o"
PAYMENT_QUESTION = "ما هي نسبة الدفعة المقدمة في خطة التقسيط A؟"
PROPERTY_QUESTION = "Is there a fully finished villa with a private garden available?"

created_conversation_ids: list[str] = []


def has_sources_column() -> bool:
    with get_session_factory().begin() as session:
        return session.execute(
            text(
                "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name = 'messages' AND column_name = 'sources'"
            )
        ).scalar_one_or_none() is not None


def missing_preconditions() -> list[str]:
    problems = []
    if not has_sources_column():
        problems.append("عمود messages.sources مش موجود — طبّق migrations/001_add_messages_sources.sql")
    try:
        get_settings()
    except ValidationError:
        problems.append("OPENROUTER_API_KEY فاضي أو مش موجود في backend/.env")
    return problems


def parse_sse(body: str) -> list[tuple[str, dict]]:
    """'event: x\\ndata: {...}\\n\\n' → [(x, {...})]."""
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


def payment_body() -> dict:
    # مفيش category: بتتحدد جوه الـagent من السؤال (السؤال واضح إنه payment_policies).
    # مفيش role ولا user_id: بيتقروا من الـJWT على السيرفر (app/auth/dependencies.py).
    return {"message": PAYMENT_QUESTION, "model": CHAT_MODEL}


def conversation_ids(client: TestClient, token: str) -> list[str]:
    response = client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    return [conversation["id"] for conversation in response.json()]


def stored_messages(client: TestClient, conversation_id: str, token: str) -> list[dict]:
    response = client.get(f"/conversations/{conversation_id}", headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    return response.json()["messages"]


def case_models_lists_chat_model(client: TestClient) -> bool:
    """/models لازم يرجع الموديلات المجانية، ومنها الموديل اللي الحالات الجاية بتستخدمه."""
    response = client.get("/models")
    ids = [model["id"] for model in response.json()] if response.status_code == 200 else []
    print(f"  status={response.status_code} | {len(ids)} موديل مجاني")
    print(f"  {CHAT_MODEL} موجود: {CHAT_MODEL in ids}")
    return CHAT_MODEL in ids


def case_unauthenticated_rejected(client: TestClient) -> bool:
    """/chat من غير Authorization → 401 قبل أي كتابة (مش 422 ولا 403 بلسيبة)."""
    before = client.get("/conversations")
    response = client.post("/chat", json=payment_body())
    after = client.get("/conversations")
    print(
        f"  /chat بدون token: {response.status_code} (متوقع 401) | "
        f"/conversations بدون token: {before.status_code} و{after.status_code} (متوقع 401)"
    )
    return response.status_code == 401 and before.status_code == 401 and after.status_code == 401


def case_sales_chat_streams_and_persists(client: TestClient, token: str) -> bool:
    """Sales → tokens بـSSE، وبعدين الرد نفسه والمصادر نفسها يتحفظوا في messages."""
    response = post_chat(client, token, payment_body())
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = parse_sse(response.text)
    tokens = [payload["text"] for name, payload in events if name == "token"]
    answer = "".join(tokens)
    print(f"  events: {len(tokens)} token + {[name for name, _ in events if name != 'token']}")
    print(f"  الرد:\n    {answer[:400]}")
    if not tokens or events[-1][0] != "done":
        return False

    sources = events[-1][1]["sources"]
    print(f"  المصادر: {sorted({(s['doc_title'], s['version']) for s in sources})}")
    conversation_id = response.headers["x-conversation-id"]
    messages = stored_messages(client, conversation_id, token)
    return (
        bool(sources)
        and [m["role"] for m in messages] == ["user", "assistant"]
        and messages[1]["content"] == answer
        and messages[1]["sources"] == sources
        and conversation_id in conversation_ids(client, token)
    )


def case_hr_property_listings_denied(client: TestClient, token: str) -> bool:
    """HR يسأل سؤال واضح إنه property_listings → الـagent يوجّهه هناك → فحص الصلاحية
    بيرفض: event واحد denied، والرفض **بيتحفظ** كرد assistant بنص رسالة الرفض
    بالظبط (بدون أي تفاصيل داخلية زي الـcategory المقترحة) — قرار معتمد في
    Phase 2 (قبل كده الرفض مكانش بيتحفظ خالص)."""
    response = post_chat(client, token, {"message": PROPERTY_QUESTION, "model": CHAT_MODEL})
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = parse_sse(response.text)
    print(f"  events: {events}")
    if [name for name, _ in events] != ["denied"]:
        return False
    denial_message = events[0][1]["message"]
    print(f"  رسالة الرفض: {denial_message}")
    conversation_id = response.headers.get("x-conversation-id")
    print(f"  X-Conversation-Id موجود: {bool(conversation_id)}")
    if not conversation_id:
        return False
    messages = stored_messages(client, conversation_id, token)
    print(f"  الرسايل المحفوظة: {[m['role'] for m in messages]}")
    return (
        [m["role"] for m in messages] == ["user", "assistant"]
        and messages[1]["content"] == denial_message
        and messages[1]["sources"] == []
        and conversation_id in conversation_ids(client, token)
    )


def case_paid_model_rejected_before_any_write(client: TestClient, token: str) -> bool:
    """موديل مدفوع → 422 قبل ما أي محادثة تتعمل (ماينفعش يتحاسب على الـAPI key بتاعنا)."""
    before = conversation_ids(client, token)
    response = post_chat(client, token, {**payment_body(), "model": PAID_MODEL})
    after = conversation_ids(client, token)
    print(f"  status={response.status_code} | عدد المحادثات قبل/بعد: {len(before)}/{len(after)}")
    return response.status_code == 422 and before == after


def delete_created_conversations() -> None:
    # messages بتتمسح معاها (on delete cascade).
    with get_session_factory().begin() as session:
        for conversation_id in created_conversation_ids:
            session.execute(
                text("DELETE FROM public.conversations WHERE id = :id"), {"id": conversation_id}
            )


def run_cases(client: TestClient, tokens: dict[str, str]) -> int:
    """يرجّع عدد الحالات اللي فشلت."""
    cases: list[tuple[str, Callable[[], bool]]] = [
        ("GET /models (متوقع: فيه الموديل المجاني)", lambda: case_models_lists_chat_model(client)),
        ("/chat و/conversations بدون Authorization (متوقع: 401)", lambda: case_unauthenticated_rejected(client)),
        ("sales → /chat payment_policies (متوقع: stream + حفظ)",
         lambda: case_sales_chat_streams_and_persists(client, tokens["sales"])),
        ("hr → /chat (الـagent يوجّه سؤال الوحدات لـproperty_listings) (متوقع: denied + حفظ الرفض)",
         lambda: case_hr_property_listings_denied(client, tokens["hr"])),
        ("sales → /chat بموديل مدفوع (متوقع: 422)",
         lambda: case_paid_model_rejected_before_any_write(client, tokens["sales"])),
    ]
    failed = 0
    for title, case in cases:
        print(f"\n=== {title} ===")
        passed = case()
        failed += not passed
        print(f"  → {'✅ PASS' if passed else '❌ FAIL'}")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return failed


def main() -> None:
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
            failed = run_cases(client, tokens)
        finally:
            delete_created_conversations()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
