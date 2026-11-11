"""
POST /chat — سؤال الموظف → agent (LangGraph) → إجابة من OpenRouter بـstreaming (SSE).

الفلو جوه الـgraph (PRD قسم 6): تحديد الـcategory بقرار LLM (agentic) → فحص
صلاحية deterministic → retrieval بالصلاحيات → إجابة grounded. الـcategory
بتيجي من الـagent مش من الـrequest — الـclient ملوش كلمة فيها خالص.

بروتوكول الـSSE — الـdata في كل event عبارة عن JSON، عشان الـnewlines جوه النص
ماتكسرش الـSSE framing:
    event: token   data: {"text": "..."}         مرة أو أكتر
    event: done    data: {"sources": [...]}      آخر event في أي رد اتحفظ
    event: denied  data: {"message": "..."}      event واحد بس — رسالة الرفض نفسها
    event: error   data: {"message": "..."}      فشل داخلي أو فشل الموديل

الكتابة في الداتابيز (invariant):
- المحادثة الجديدة ورسالة الموظف بيتكتبوا **بعد ما مصير الطلب يتحسم** جوه
  الـgraph (رفض / مش لاقي / فيه إجابة) — مافيش أي استثناء غير متوقع يسيب
  محادثة ورسالة user من غير أي رد محفوظ.
- الرفض دلوقتي **بيتحفظ** كرد assistant بنص رسالة الرفض اللي ظهرت للموظف
  بالظبط (من غير الـcategory المقترحة ولا أي تفاصيل داخلية) — فمحادثة جديدة
  على الرفض بترجّع X-Conversation-Id برضه.
- الرد الجاهز "مش لاقي ده في بيانات الشركة" بيتحفظ برضه بـsources فاضية
  (رد حقيقي بعد بحث حصل فعلاً)، والـretrieval/الـagent فشل استثناءً = مفيش
  أي كتابة.
"""

import json
import logging
from collections.abc import AsyncGenerator, Iterable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints, field_validator
from sqlalchemy.exc import IntegrityError

from app.agent.graph import get_compiled_graph
from app.agent.nodes import EMPTY_ANSWER_MESSAGE
from app.api.models import fetch_free_models_or_502
from app.db.conversation_store import add_message, create_conversation, find_conversation
from app.llm.prompts import NOT_FOUND_MESSAGE
from app.rag.retrieval import ROLE_ALLOWED_CATEGORIES, RetrievedChunk

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

TITLE_MAX_CHARS = 50
MESSAGE_MAX_CHARS = 4000
RETRIEVAL_ERROR_MESSAGE = "حصل خطأ في البحث في بيانات الشركة — جرّب تاني."


class ChatRequest(BaseModel):
    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX_CHARS)
    ]
    # TEMPORARY: replace with JWT-derived role/user_id once auth is built
    role: str
    # TEMPORARY: replace with JWT-derived role/user_id once auth is built
    user_id: UUID
    conversation_id: UUID | None = None
    model: Annotated[str, StringConstraints(min_length=1)]

    # بنرفض الـrole المش معروف هنا (422) قبل ما نكتب أي حاجة في الداتابيز.
    # الـcategory مبقتش مدخل من الـclient أصلاً — بتتحدد جوه الـagent، والـallowlist
    # بتاعتها في app/agent/nodes.py.
    @field_validator("role")
    @classmethod
    def _role_is_known(cls, role: str) -> str:
        if role not in ROLE_ALLOWED_CATEGORIES:
            raise ValueError(f"دور غير معروف: {role!r}")
        return role


async def require_free_model(body: ChatRequest) -> ChatRequest:
    """
    الموديل لازم يكون في قائمة OpenRouter المجانية — غير كده الـclient يقدر
    يطلب موديل مدفوع على حساب الـAPI key بتاعنا.
    """
    free_ids = {model["id"] for model in await fetch_free_models_or_502()}
    if body.model not in free_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"الموديل {body.model!r} مش من الموديلات المجانية المتاحة دلوقتي — راجع GET /models.",
        )
    return body


@router.post("/chat")
async def chat(body: Annotated[ChatRequest, Depends(require_free_model)]) -> StreamingResponse:
    """سؤال → agent → حفظ → رد streaming (راجع بروتوكول الـSSE وinvariant الكتابة فوق)."""
    await _require_owned_conversation(body)
    stream = _start_agent_stream(body)
    state = await _await_outcome(stream)
    if state is None:
        return _sse_response(body.conversation_id, [_sse_event("error", {"message": RETRIEVAL_ERROR_MESSAGE})])

    if state.get("permission_result") == "denied":
        denial_message = state.get("denial_message") or ""
        conversation_id = await _persist_turn(body, assistant_reply=denial_message)
        return _sse_response(conversation_id, [_sse_event("denied", {"message": denial_message})])

    if not state.get("retrieval_ok"):
        conversation_id = await _persist_turn(body, assistant_reply=NOT_FOUND_MESSAGE)
        return _sse_response(
            conversation_id,
            [_sse_event("token", {"text": NOT_FOUND_MESSAGE}), _sse_event("done", {"sources": []})],
        )

    conversation_id = await _persist_turn(body)
    return _sse_response(conversation_id, _forward_answer(stream, conversation_id, state))


async def _require_owned_conversation(body: ChatRequest) -> None:
    # قراية بس عشان الـ404 يرجع قبل ما نصرف embedding أو LLM request على request هيترفض عادي.
    if body.conversation_id is None:
        return
    found = await run_in_threadpool(find_conversation, body.conversation_id, body.user_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة مش موجودة.")


def _start_agent_stream(body: ChatRequest) -> AsyncGenerator:
    return get_compiled_graph().astream(
        {
            "user_id": body.user_id,
            "role": body.role,
            "question": body.message,
            "conversation_id": body.conversation_id,
            "model": body.model,
        },
        stream_mode=["custom", "values"],
    )


async def _await_outcome(stream: AsyncGenerator) -> dict | None:
    """
    مرحلة الحسم: بتسحب الـstream لحد ما مصير الطلب يتحسم (denied / مش لاقي /
    فيه إجابة). مافيش tokens جايين قبل كده — respond هو أول من يكتب على الـstream
    وبييجي بعد الـretrieval، فمافيش حاجة بتضيع من التخطي ده. None = فشل داخلي.
    """
    state: dict = {}
    try:
        async for mode, chunk in stream:
            if mode != "values":
                continue
            state = chunk
            if chunk.get("retrieval_ok"):
                break  # فيه إجابة جاية — باقي الـstream (tokens) للـresponse تحت
    except Exception:
        logger.exception("Agent failed before retrieval outcome (role=%s)", state.get("role"))
        return None
    return state


async def _persist_turn(body: ChatRequest, assistant_reply: str | None = None) -> UUID:
    """محادثة جديدة (بالـtitle = أول 50 حرف من السؤال) لو مفيش، + رسالة الموظف، + الرد الجاهز لو فيه."""
    conversation_id = body.conversation_id or await _create_conversation(body)
    await run_in_threadpool(add_message, conversation_id, "user", body.message, sources=[])
    if assistant_reply is not None:
        await run_in_threadpool(add_message, conversation_id, "assistant", assistant_reply, sources=[])
    return conversation_id


async def _create_conversation(body: ChatRequest) -> UUID:
    try:
        return await run_in_threadpool(create_conversation, body.user_id, body.message[:TITLE_MAX_CHARS])
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="الموظف ده مش موجود."
        ) from exc


async def _forward_answer(
    stream: AsyncGenerator, conversation_id: UUID, state: dict
) -> AsyncGenerator[str, None]:
    """يكمل الـgraph stream: tokens من respond → SSE، وبعد ما يخلص يحفظ الرد بالمصادر."""
    answer_parts: list[str] = []
    try:
        async for mode, chunk in stream:
            if mode != "custom":
                continue
            if chunk.get("type") == "token":
                answer_parts.append(chunk["text"])
                yield _sse_event("token", {"text": chunk["text"]})
            elif chunk.get("type") == "error":
                yield _sse_event("error", {"message": chunk["message"]})
                return
    except Exception:
        logger.exception("Agent streaming failed (role=%s)", state.get("role"))
        yield _sse_event("error", {"message": RETRIEVAL_ERROR_MESSAGE})
        return

    answer = "".join(answer_parts)
    # حماية زيادة: stream خلص من غير token ولا error (مش المفروض يحصل —
    # respond بيكتب error event في الحالتين) — مايحفظش رد فاضي أصلاً.
    if not answer.strip():
        yield _sse_event("error", {"message": EMPTY_ANSWER_MESSAGE})
        return

    sources = [_source_entry(chunk) for chunk in state.get("retrieved_chunks", [])]
    await run_in_threadpool(add_message, conversation_id, "assistant", answer, sources)
    yield _sse_event("done", {"sources": sources})


def _source_entry(chunk: RetrievedChunk) -> dict:
    return {
        "chunk_id": str(chunk.chunk_id),
        "doc_id": chunk.doc_id,
        "doc_title": chunk.doc_title,
        "version": chunk.metadata.version,
        "section": chunk.metadata.section,
        "similarity_score": round(chunk.similarity_score, 4),
    }


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_response(
    conversation_id: UUID | None, events: Iterable[str] | AsyncGenerator[str, None]
) -> StreamingResponse:
    headers = {"Cache-Control": "no-cache"}
    if conversation_id is not None:
        headers["X-Conversation-Id"] = str(conversation_id)
    return StreamingResponse(events, media_type="text/event-stream", headers=headers)
