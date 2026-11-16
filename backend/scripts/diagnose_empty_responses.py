"""
تشخيص مؤقت (مش production code) لفشل حالتي hr_broad وmemory برسالة الرد الفاضي
من nvidia/nemotron-3.5-lightning:free.

بيشغّل الحالتين بنفس شكل test_agent_routing.py (عبر TestClient على app الحقيقي
والـgraph كامل) لكن مع اعتراض نداءات OpenRouter وقت التشغيل (monkeypatch على
app.agent.nodes) وتسجيل الـresponse الخام كامل لأي رد فاضي أو فاشل — عشان نعرف:
فاضي فعلاً ولا refusal ولا finish_reason=length ولا حاجة تانية.

بيشغّل كل حالة 3 مرات منفصلة لفحص قابلية إعادة الإنتاج، ويطبع ملخص لكل نداء.
المحادثات اللي بيعملها بتتمسح في الآخر. الاستهلاك التقديري: ~18 LLM request.

طريقة التشغيل (من backend/ والـvenv مفعّلة):
    python -m scripts.diagnose_empty_responses
"""

import json
import sys
import time
from uuid import UUID

import httpx
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from openai import APIError
from sqlalchemy import text

import app.agent.nodes as nodes
from app.core.config import get_settings
from app.db.session import get_session_factory

CHAT_MODEL = "nvidia/nemotron-3.5-lightning:free"
BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 2048
HTTP_TIMEOUT_SECONDS = 180.0
RAW_BODY_LOG_LIMIT = 12000

BROAD_QUESTION = "What units are available, how much do they cost, and how can I contact the company?"
MEMORY_TURN_1 = "What unit types exist in Marina Heights?"
MEMORY_TURN_2 = "How much is the cheapest one?"

records: list[dict] = []


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {get_settings().openrouter_api_key.get_secret_value()}"}


def record(kind: str, case: str, attempt: int, **fields) -> None:
    entry = {"t": time.strftime("%H:%M:%S"), "case": case, "kind": kind, "attempt": attempt, **fields}
    records.append(entry)
    print(json.dumps(entry, ensure_ascii=False, default=str))


def truncate(text_value: str) -> str:
    if len(text_value) <= RAW_BODY_LOG_LIMIT:
        return text_value
    return text_value[:RAW_BODY_LOG_LIMIT] + f" …(مقطوع، الإجمالي {len(text_value)} حرف)"


async def raw_post_json(payload: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as hc:
        return await hc.post(f"{BASE_URL}/chat/completions", headers=auth_headers(), json=payload)


def summarize_choice(data: dict) -> dict:
    choices = data.get("choices") or [{}]
    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
    return {
        "finish_reason": choice.get("finish_reason"),
        "content_chars": len(content.strip()),
        "reasoning_chars": len(reasoning.strip()),
        "native_finish_reason": choice.get("native_finish_reason"),
        "error_field": data.get("error"),
        "usage": data.get("usage"),
        "provider": data.get("provider"),
    }


async def instrumented_complete_chat(model: str, messages: list[dict]) -> str:
    """نفس عقد complete_chat (محاولتين، max_tokens=2048، غير streaming) مع تسجيل خام."""
    payload = {"model": model, "messages": messages, "max_tokens": MAX_TOKENS}
    for attempt in (1, 2):
        try:
            response = await raw_post_json(payload)
        except Exception as exc:
            record("decision", CURRENT_CASE[0], attempt, status="exception", error=repr(exc))
            continue
        if response.status_code != 200:
            record("decision", CURRENT_CASE[0], attempt, status=response.status_code, raw=truncate(response.text))
            continue
        data = response.json()
        summary = summarize_choice(data)
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        empty = not content.strip()
        record(
            "decision", CURRENT_CASE[0], attempt,
            status=200, empty=empty, **summary,
            raw=truncate(response.text) if empty else None,
        )
        if not empty:
            return content
    return ""


def collect_stream_line(line: str, state: dict) -> None:
    if not line.startswith("data:"):
        return
    data = line[5:].strip()
    if data == "[DONE]":
        return
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        state["raw_lines"].append(line)
        return
    state["raw_lines"].append(line)
    if obj.get("error"):
        state["stream_error"] = obj["error"]
    for choice in obj.get("choices") or []:
        delta = choice.get("delta") or {}
        if delta.get("content"):
            state["parts"].append(delta["content"])
        if delta.get("reasoning"):
            state["saw_reasoning"] = True
        if choice.get("finish_reason"):
            state["finish_reason"] = choice["finish_reason"]
    if obj.get("usage"):
        state["usage"] = obj["usage"]


async def instrumented_stream_chat_completion(model: str, messages: list[dict]):
    """نفس عقد stream_chat_completion (محاولة واحدة، streaming) مع تسجيل خام."""
    payload = {"model": model, "messages": messages, "stream": True, "max_tokens": MAX_TOKENS}
    state: dict = {"parts": [], "raw_lines": [], "saw_reasoning": False, "finish_reason": None, "usage": None, "stream_error": None}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as hc:
        try:
            async with hc.stream("POST", f"{BASE_URL}/chat/completions", headers=auth_headers(), json=payload) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    record("answer", CURRENT_CASE[0], 1, status=response.status_code, raw=truncate(body))
                    raise APIError(f"OpenRouter HTTP {response.status_code}", request=None, body=body)
                async for line in response.aiter_lines():
                    collect_stream_line(line, state)
        except APIError:
            raise
        except Exception as exc:
            record("answer", CURRENT_CASE[0], 1, status="exception", error=repr(exc))
            raise APIError(repr(exc), request=None) from exc
    answer = "".join(state["parts"])
    empty = not answer.strip()
    record(
        "answer", CURRENT_CASE[0], 1,
        status=200, empty=empty,
        finish_reason=state["finish_reason"],
        content_chars=len(answer.strip()),
        saw_reasoning=state["saw_reasoning"],
        stream_error=state["stream_error"],
        usage=state["usage"],
        raw=truncate("\n".join(state["raw_lines"])) if empty else None,
    )
    for text_part in state["parts"]:
        yield text_part


def instrument_nodes(case: str) -> None:
    CURRENT_CASE[0] = case
    nodes.complete_chat = instrumented_complete_chat
    nodes.stream_chat_completion = instrumented_stream_chat_completion


CURRENT_CASE = ["?"]


def find_user_id(role: str) -> UUID | None:
    with get_session_factory().begin() as session:
        return session.execute(
            text("SELECT id FROM public.profiles WHERE role = :role LIMIT 1"), {"role": role}
        ).scalar_one_or_none()


def quota_status() -> dict:
    with httpx.Client(timeout=15.0) as hc:
        response = hc.get(f"{BASE_URL}/key", headers=auth_headers())
        data = response.json().get("data") or {}
    return {
        "usage": data.get("usage"),
        "limit": data.get("limit"),
        "rate_limit": data.get("rate_limit"),
    }


def sse_summary(response) -> str:
    if response.status_code != 200:
        return f"HTTP {response.status_code}: {response.text[:300]}"
    names = []
    for block in response.text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines())
        if "event" in fields:
            names.append(fields["event"])
    return " + ".join(names)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    sales_id = find_user_id("sales")
    hr_id = find_user_id("hr")
    if sales_id is None or hr_id is None:
        print("المتطلبات مش جاهزة — مفيش sales/hr في profiles")
        sys.exit(2)
    print(f"الـquota قبل: {json.dumps(quota_status(), ensure_ascii=False)}")

    from app.main import app

    created_conversations: list[str] = []
    results: dict[str, list[bool]] = {"hr_broad": [], "memory": []}

    with TestClient(app) as client:
        def post(body: dict):
            response = client.post("/chat", json=body)
            if conversation_id := response.headers.get("x-conversation-id"):
                created_conversations.append(conversation_id)
            return response

        try:
            print("\n########## hr_broad × 3 ##########")
            instrument_nodes("hr_broad")
            for attempt in range(1, 4):
                records.clear()
                response = post({"message": BROAD_QUESTION, "role": "hr", "user_id": str(hr_id), "model": CHAT_MODEL})
                print(f"[hr_broad #{attempt}] SSE: {sse_summary(response)}")
                results["hr_broad"].append("error" not in sse_summary(response) and response.status_code == 200)

            print("\n########## memory × 3 ##########")
            instrument_nodes("memory")
            for attempt in range(1, 4):
                records.clear()
                first = post({"message": MEMORY_TURN_1, "role": "sales", "user_id": str(sales_id), "model": CHAT_MODEL})
                first_summary = sse_summary(first)
                if first.status_code != 200:
                    print(f"[memory #{attempt}] الدور الأول: HTTP {first.status_code}")
                    results["memory"].append(False)
                    continue
                conversation_id = first.headers["x-conversation-id"]
                second = post({
                    "message": MEMORY_TURN_2, "role": "sales", "user_id": str(sales_id),
                    "model": CHAT_MODEL, "conversation_id": conversation_id,
                })
                second_summary = sse_summary(second)
                print(f"[memory #{attempt}] الدور الأول: {first_summary} | الدور التاني: {second_summary}")
                results["memory"].append("error" not in second_summary and "error" not in first_summary)
        finally:
            with get_session_factory().begin() as session:
                for conversation_id in created_conversations:
                    session.execute(text("DELETE FROM public.conversations WHERE id = :id"), {"id": conversation_id})

    print("\n########## ملخص قابلية إعادة الإنتاج ##########")
    for case_name, outcomes in results.items():
        print(f"{case_name}: {outcomes.count(True)}/{len(outcomes)} نجحت | {outcomes}")
    print(f"\nالـquota بعد: {json.dumps(quota_status(), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
