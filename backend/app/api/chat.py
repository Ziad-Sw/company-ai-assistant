"""
POST /chat — سؤال الموظف → retrieval بالصلاحيات → إجابة من OpenRouter بـstreaming (SSE).

بروتوكول الـSSE — الـdata في كل event عبارة عن JSON، عشان الـnewlines جوه النص
ماتكسرش الـSSE framing:
    event: token   data: {"text": "..."}         مرة أو أكتر
    event: done    data: {"sources": [...]}      آخر event في أي رد اتحفظ
    event: denied  data: {"message": "..."}      event واحد بس، من غير LLM
    event: error   data: {"message": "..."}      الـretrieval أو OpenRouter فشل؛ الرد مش بيتحفظ

الـdenied والـerror معناهم إن **مفيش أي كتابة حصلت** في conversations أو messages —
المحادثة الجديدة بتتعمل ورسالة الموظف بتتحفظ بعد ما الـretrieval ينجح بس
(مفيش orphan rows). الـconversation_id بيرجع في header ‏X-Conversation-Id
(الـclient محتاجه لو المحادثة جديدة) — ومش موجود في الـdenied/error لمحادثة جديدة
لأن مفيش حاجة اتعملت أصلاً.
"""

import json
import logging
from collections.abc import AsyncGenerator, Iterable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from openai import APIError
from pydantic import BaseModel, StringConstraints, field_validator
from sqlalchemy.exc import IntegrityError

from app.api.models import fetch_free_models_or_502
from app.db.conversation_store import add_message, create_conversation, find_conversation
from app.llm.openrouter_client import stream_chat_completion
from app.llm.prompts import NOT_FOUND_MESSAGE, build_grounded_system_prompt
from app.rag.retrieval import (
    ALL_CATEGORIES,
    ROLE_ALLOWED_CATEGORIES,
    PermissionDeniedError,
    RetrievedChunk,
    retrieve_chunks,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

TOP_K = 5
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
    category: str | None = None
    model: Annotated[str, StringConstraints(min_length=1)]

    # بنرفض role/category المش معروفين هنا (422) قبل ما نكتب أي حاجة في الداتابيز.
    # "معروفة بس مش مسموحة" مش هنا — دي بتوصل لـretrieve_chunks وبترجع denied.
    @field_validator("role")
    @classmethod
    def _role_is_known(cls, role: str) -> str:
        if role not in ROLE_ALLOWED_CATEGORIES:
            raise ValueError(f"دور غير معروف: {role!r}")
        return role

    @field_validator("category")
    @classmethod
    def _category_is_known(cls, category: str | None) -> str | None:
        if category is not None and category not in ALL_CATEGORIES:
            raise ValueError(f"category غير معروفة: {category!r}")
        return category


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
def chat(body: Annotated[ChatRequest, Depends(require_free_model)]) -> StreamingResponse:
    """سؤال → retrieval بالصلاحيات → حفظ → رد streaming (راجع بروتوكول الـSSE فوق)."""
    # قراية بس عشان الـ404 يرجع قبل ما نصرف embedding على request هيترفض عادي.
    if body.conversation_id is not None and find_conversation(
        body.conversation_id, body.user_id
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة مش موجودة.")

    try:
        # TEMPORARY: naive retrieval, replace with LangGraph agent's category routing in the next phase
        chunks = retrieve_chunks(
            query=body.message, role=body.role, category=body.category, top_k=TOP_K
        )
    except PermissionDeniedError as exc:
        return _sse_response(body.conversation_id, [_sse_event("denied", {"message": str(exc)})])
    except Exception:
        logger.exception("Retrieval failed (role=%s, category=%s)", body.role, body.category)
        return _sse_response(
            body.conversation_id, [_sse_event("error", {"message": RETRIEVAL_ERROR_MESSAGE})]
        )

    # الـretrieval نجح — بعد كده بس المنشأة الجديدة ورسالة الموظف بيتكتبوا.
    conversation_id = body.conversation_id or _create_conversation(body)
    add_message(conversation_id, "user", body.message, sources=[])

    if not chunks:
        add_message(conversation_id, "assistant", NOT_FOUND_MESSAGE, sources=[])
        return _sse_response(
            conversation_id,
            [_sse_event("token", {"text": NOT_FOUND_MESSAGE}), _sse_event("done", {"sources": []})],
        )

    return _sse_response(
        conversation_id, _stream_grounded_answer(conversation_id, body, chunks)
    )


def _create_conversation(body: ChatRequest) -> UUID:
    """محادثة جديدة بالـtitle = أول 50 حرف من السؤال."""
    try:
        return create_conversation(body.user_id, title=body.message[:TITLE_MAX_CHARS])
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="الموظف ده مش موجود."
        ) from exc


async def _stream_grounded_answer(
    conversation_id: UUID, body: ChatRequest, chunks: list[RetrievedChunk]
) -> AsyncGenerator[str, None]:
    """يعمل stream لرد الموديل، وبعد ما يخلص يحفظه بالمصادر اللي اتبعتتله."""
    messages = [
        {"role": "system", "content": build_grounded_system_prompt(chunks)},
        {"role": "user", "content": body.message},
    ]
    answer_parts: list[str] = []
    try:
        async for text in stream_chat_completion(body.model, messages):
            answer_parts.append(text)
            yield _sse_event("token", {"text": text})
    except APIError as exc:
        logger.warning("OpenRouter streaming failed (model=%s): %r", body.model, exc)
        yield _sse_event("error", {"message": "الموديل مارجّعش رد — جرّب تاني أو اختار موديل تاني."})
        return

    answer = "".join(answer_parts)
    # موديلات الـreasoning المجانية ساعات بتخلص من غير ولا token في content.
    if not answer.strip():
        yield _sse_event("error", {"message": "الموديل رجّع رد فاضي — جرّب تاني أو اختار موديل تاني."})
        return

    sources = [_source_entry(chunk) for chunk in chunks]
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
