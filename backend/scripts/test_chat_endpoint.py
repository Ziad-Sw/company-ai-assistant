"""
اختبار يدوي لـ/chat و/models و/conversations على الداتابيز وOpenRouter الحقيقيين.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.test_chat_endpoint

محتاج قبل التشغيل (السكريبت بيتأكد منهم الأول ويقولك الناقص):
  - OPENROUTER_API_KEY وDATABASE_URL وGEMINI_API_KEY في الـ.env
  - migrations/001_add_messages_sources.sql متطبّقة
  - موظف sales وموظف hr على الأقل في profiles (docs/demo-accounts.md)

بيستهلك: 1 request من Gemini embedding، و1 chat request من الـ50 المجانية في اليوم
بتاعة OpenRouter، وقائمة /models بتتجلب من OpenRouter مرة واحدة (بتتخزن in-memory
بـ5 دقايق). المحادثات اللي بيعملها بتتمسح في الآخر.
الـexit code: 0 لو كله نجح، 1 لو أي حالة فشلت، 2 لو المتطلبات مش جاهزة.
"""

import json
import sys
from collections.abc import Callable
from uuid import UUID

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory

# موديل محدد ومسمّى مش الـauto-router (openrouter/free): الـrouter بيختار موديل
# عشوائي وممكن يرجّع رد فاضي أو rate limit، فالاختبار بيبقى غير deterministic.
CHAT_MODEL = "nvidia/nemotron-3.5-lightning:free"
PAID_MODEL = "openai/gpt-4o"
PAYMENT_QUESTION = "ما هي نسبة الدفعة المقدمة في خطة التقسيط A؟"
PROPERTY_QUESTION = "Is there a fully finished villa with a private garden available?"

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


def missing_preconditions(user_ids: dict[str, UUID | None]) -> list[str]:
    problems = [
        f"مفيش موظف role={role} في profiles — اعمل seed للـdemo accounts (docs/demo-accounts.md)"
        for role, user_id in user_ids.items()
        if user_id is None
    ]
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


def post_chat(client: TestClient, body: dict) -> Response:
    response = client.post("/chat", json=body)
    if conversation_id := response.headers.get("x-conversation-id"):
        created_conversation_ids.append(conversation_id)
    return response


def sales_payment_body(user_id: UUID) -> dict:
    return {
        "message": PAYMENT_QUESTION, "role": "sales", "user_id": str(user_id),
        "category": "payment_policies", "model": CHAT_MODEL,
    }


def conversation_ids(client: TestClient, user_id: UUID) -> list[str]:
    response = client.get("/conversations", params={"user_id": str(user_id)})
    response.raise_for_status()
    return [conversation["id"] for conversation in response.json()]


def stored_messages(client: TestClient, conversation_id: str, user_id: UUID) -> list[dict]:
    response = client.get(f"/conversations/{conversation_id}", params={"user_id": str(user_id)})
    response.raise_for_status()
    return response.json()["messages"]


def case_models_lists_chat_model(client: TestClient) -> bool:
    """/models لازم يرجع الموديلات المجانية، ومنها الموديل اللي الحالات الجاية بتستخدمه."""
    response = client.get("/models")
    ids = [model["id"] for model in response.json()] if response.status_code == 200 else []
    print(f"  status={response.status_code} | {len(ids)} موديل مجاني")
    print(f"  {CHAT_MODEL} موجود: {CHAT_MODEL in ids}")
    return CHAT_MODEL in ids


def case_sales_chat_streams_and_persists(client: TestClient, user_id: UUID) -> bool:
    """Sales → tokens بـSSE، وبعدين الرد نفسه والمصادر نفسها يتحفظوا في messages."""
    response = post_chat(client, sales_payment_body(user_id))
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
    messages = stored_messages(client, conversation_id, user_id)
    return (
        bool(sources)
        and [m["role"] for m in messages] == ["user", "assistant"]
        and messages[1]["content"] == answer
        and messages[1]["sources"] == sources
        and conversation_id in conversation_ids(client, user_id)
    )


def case_hr_property_listings_denied(client: TestClient, user_id: UUID) -> bool:
    """HR → property_listings: event واحد denied، ومفيش أي كتابة في الداتابيز
    (ولا محادثة جديدة ولا رسالة — الكتابة بعد ما الـretrieval ينجح بس)."""
    conversations_before = conversation_ids(client, user_id)
    response = post_chat(client, {
        "message": PROPERTY_QUESTION, "role": "hr", "user_id": str(user_id),
        "category": "property_listings", "model": CHAT_MODEL,
    })
    print(f"  status={response.status_code}")
    if response.status_code != 200:
        print(f"  {response.text}")
        return False
    events = parse_sse(response.text)
    print(f"  events: {events}")
    if [name for name, _ in events] != ["denied"]:
        return False
    # محادثة جديدة مكانتش موجودة: مفيش X-Conversation-Id لأن مفيش حاجة اتعملت.
    print(f"  X-Conversation-Id موجود: {bool(response.headers.get('x-conversation-id'))}")
    wrote_something = bool(
        response.headers.get("x-conversation-id")
        or conversation_ids(client, user_id) != conversations_before
    )
    print(f"  حصلت كتابة في الداتابيز: {wrote_something}")
    return not wrote_something


def case_paid_model_rejected_before_any_write(client: TestClient, user_id: UUID) -> bool:
    """موديل مدفوع → 422 قبل ما أي محادثة تتعمل (ماينفعش يتحاسب على الـAPI key بتاعنا)."""
    before = conversation_ids(client, user_id)
    response = post_chat(client, {**sales_payment_body(user_id), "model": PAID_MODEL})
    after = conversation_ids(client, user_id)
    print(f"  status={response.status_code} | عدد المحادثات قبل/بعد: {len(before)}/{len(after)}")
    return response.status_code == 422 and before == after


def delete_created_conversations() -> None:
    # messages بتتمسح معاها (on delete cascade).
    with get_session_factory().begin() as session:
        for conversation_id in created_conversation_ids:
            session.execute(
                text("DELETE FROM public.conversations WHERE id = :id"), {"id": conversation_id}
            )


def run_cases(client: TestClient, user_ids: dict[str, UUID]) -> int:
    """يرجّع عدد الحالات اللي فشلت."""
    cases: list[tuple[str, Callable[[], bool]]] = [
        ("GET /models (متوقع: فيه الموديل المجاني)", lambda: case_models_lists_chat_model(client)),
        ("sales → /chat payment_policies (متوقع: stream + حفظ)",
         lambda: case_sales_chat_streams_and_persists(client, user_ids["sales"])),
        ("hr → /chat property_listings (متوقع: denied)",
         lambda: case_hr_property_listings_denied(client, user_ids["hr"])),
        ("sales → /chat بموديل مدفوع (متوقع: 422)",
         lambda: case_paid_model_rejected_before_any_write(client, user_ids["sales"])),
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
    user_ids = {role: find_user_id(role) for role in ("sales", "hr")}
    if problems := missing_preconditions(user_ids):
        print("المتطلبات مش جاهزة:\n" + "\n".join(f"  - {p}" for p in problems))
        sys.exit(2)

    # import هنا مش فوق: app.main بيعمل fail fast لو OPENROUTER_API_KEY ناقص،
    # وعايزين رسالة المتطلبات اللي فوق تظهر الأول بدل traceback.
    from app.main import app

    try:
        failed = run_cases(TestClient(app), user_ids)
    finally:
        delete_created_conversations()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
