"""
الـnodes الخمسة بتوع الـagent (PRD قسم 6 — الفلو من السؤال للرد).

العقود الثابتة:
- check_permission كود ثابت (deterministic) مش قرار LLM — بتقرا **بس** role و
  decided_category من الـstate، ومابتشوفش السؤال ولا أي نص مولّد من الموديل،
  فمستحيل محتوى البرومبت يأثر عليها (Tech-Stack.md قسم 3 و5).
- الفرق الحرج: category **معروفة ومش مسموحة** للـrole = رفض حقيقي (PermissionDeniedError
  برسالة بتسمّي السبب — PRD نقطة 5). category **مش معروفة أصلاً** (الـLLM اختلقها)
  = فشل توجيه مش طلب وصول — بنرجّعها None (scope كامل للـrole) ومفيش رسالة
  "مش مسموح" بتوصل للموظف لأنها أصلاً مش موجودة.
- decide_category بـprompt-then-parse مع allowlist صارم: أي parse فاشل أو output
  مش معروف = fallback لـNone، والسؤال بيكمّل عادي (ممنوع نمنع الموظف لأن نداء
  الـcategory باظ).
- retrieve_chunks بتتنادى زي ما هي من غير تعديل — والـre-check الداخلي بتاعها
  لـresolve_categories بيفضل طبقة حماية تانية (defense in depth) حتى لو الـnode
  لسه فحص برضه.
- الـstreaming: respond بيكتب على الـstream writer بتاع LangGraph بعقود payload
  ثابتة اللي chat.py بيحوّلها لـSSE حرفياً:
      {"type": "token", "text": ...}   مرة أو أكتر
      {"type": "error", "message": ...}  مرة واحدة كحد أقصى
- مفيش أي node بتكتب في الداتابيز — الكتابة كلها (محادثة/رسايل/رفض) في chat.py
  بعد ما مصير الطلب يتحسم، عشان الـnodes تفضل قابلة للاختبار من غير DB.
"""

import logging
import re
from typing import Literal

from langgraph.config import get_stream_writer
from openai import APIError

from app.agent.prompts import build_category_decision_prompt
from app.agent.state import AgentState
from app.db.conversation_store import list_messages
from app.llm.openrouter_client import complete_chat, stream_chat_completion
from app.llm.prompts import build_grounded_system_prompt
from app.rag.retrieval import (
    ALL_CATEGORIES,
    PermissionDeniedError,
    resolve_categories,
    retrieve_chunks,
)

logger = logging.getLogger(__name__)

TOP_K = 5
HISTORY_MAX_MESSAGES = 10
_CATEGORY_TOKENS = ("property_listings", "payment_policies", "company_info_support", "none")

# 0.60 من قياس فعلي لتوزيع الدرجات (scripts/measure_similarity.py على الداتابيز
# الحقيقية)، مش رقم متخمين: off-topic بتقف عند ≤0.5113، وon-topic بتبدأ من ≥0.7074،
# والـborderline الغير مغطى في البيانات (إيجار/تمويل) 0.525–0.565. بيتطبق على
# الـtop-1 بس (مش كل الـchunks — رتب 2-5 في الأسئلة الصحيحة بينزلوا تحت الـ0.60
# عادي). الاستثناء المعلوم والمقبول: سؤال العقارات التجارية طلع 0.6275 وهيعد —
# بيتُقفل بself-check في مرحلة لاحقة (node بين retrieve وrespond)، مش بالـthreshold.
RETRIEVAL_RELEVANCE_THRESHOLD = 0.60

MODEL_ERROR_MESSAGE = "الموديل مارجّعش رد — جرّب تاني أو اختار موديل تاني."
EMPTY_ANSWER_MESSAGE = "الموديل رجّع رد فاضي — جرّب تاني أو اختار موديل تاني."


def load_history(state: AgentState) -> dict:
    """آخر 10 رسايل من المحادثة (جدول messages هو مصدر الحقيقة — من غير checkpointer)."""
    if state["conversation_id"] is None:
        return {"history": []}
    messages = list_messages(state["conversation_id"])[-HISTORY_MAX_MESSAGES:]
    return {"history": [{"role": message.role, "content": message.content} for message in messages]}


async def decide_category(state: AgentState) -> dict:
    """قرار الـagent: أنهي category ليها السؤال — LLM بـprompt-then-parse وallowlist صارم."""
    prompt = build_category_decision_prompt(state["question"], state["history"])
    try:
        raw = await complete_chat(state["model"], [{"role": "user", "content": prompt}])
    except APIError as exc:
        # فشل النداء نفسه (network/rate limit): نفس فلسفة الـparse الفاشل — fallback
        # آمن لـNone (scope كامل للـrole) بدل ما نمنع الموظف. الباقي (bug) بيرمى عادي.
        logger.warning("Category decision call failed (model=%s): %r", state["model"], exc)
        return {"decided_category": None}
    return {"decided_category": parse_decided_category(raw)}


def parse_decided_category(raw: str) -> str | None:
    """
    يطلّع category معروفة واحدة من رد الموديل، أو None (fallback آمن دايماً —
    None معناها بحث في كل scope الـrole المسموح، يعني فشل التوجيه مايتسربش بيانات).
    """
    reply = raw.strip().strip("`'\" .").lower()
    if reply in _CATEGORY_TOKENS:
        return None if reply == "none" else reply
    # الموديل ممكن يضيف كلام حوالين الـtoken — أول token معروف يظهر بنص الرد يحسم.
    for token in _CATEGORY_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", reply):
            return None if token == "none" else token
    return None


def check_permission(state: AgentState) -> dict:
    """فحص الصلاحية — كود ثابت، بيتكلف عن resolve_categories (مصدر الحقيقة الواحد)."""
    decided = state["decided_category"]
    if decided is not None and decided not in ALL_CATEGORIES:
        # category مختلقة: مش طلب وصول، دي فشل توجيه — بنرجّعها None عشان
        # retrieve يبحث في scope الـrole كله، ونثبّت القيمة النضيفة في الـstate.
        decided = None
    try:
        resolve_categories(state["role"], decided)
    except PermissionDeniedError as exc:
        return {"decided_category": None, "permission_result": "denied", "denial_message": str(exc)}
    return {"decided_category": decided, "permission_result": "allowed", "denial_message": None}


def retrieve(state: AgentState) -> dict:
    """retrieval بالصلاحيات + تطبيق حد الصلة على الـtop-1 (منقول من chat.py زي ما هو)."""
    chunks = retrieve_chunks(
        query=state["question"], role=state["role"], category=state["decided_category"], top_k=TOP_K
    )
    retrieval_ok = bool(chunks) and chunks[0].similarity_score >= RETRIEVAL_RELEVANCE_THRESHOLD
    return {"retrieved_chunks": chunks, "retrieval_ok": retrieval_ok}


async def respond(state: AgentState) -> dict:
    """الإجابة من الـcontext المفلتر بالصلاحيات — بنفس برومبت الـgrounded RAG بدون تغيير."""
    writer = get_stream_writer()
    messages = [
        {"role": "system", "content": build_grounded_system_prompt(state["retrieved_chunks"])},
        *state["history"],
        {"role": "user", "content": state["question"]},
    ]
    answer_parts: list[str] = []
    try:
        async for text in stream_chat_completion(state["model"], messages):
            answer_parts.append(text)
            writer({"type": "token", "text": text})
    except APIError as exc:
        logger.warning("OpenRouter streaming failed (model=%s): %r", state["model"], exc)
        writer({"type": "error", "message": MODEL_ERROR_MESSAGE})
        return {}

    # موديلات الـreasoning المجانية ساعات بتخلص من غير ولا token في content.
    if not "".join(answer_parts).strip():
        writer({"type": "error", "message": EMPTY_ANSWER_MESSAGE})
    return {}


def route_after_permission(state: AgentState) -> Literal["denied", "retrieve"]:
    return "denied" if state["permission_result"] == "denied" else "retrieve"


def route_after_retrieve(state: AgentState) -> Literal["respond", "not_found"]:
    return "respond" if state["retrieval_ok"] else "not_found"


# __all__: اللي بيستهلكه graph.py واختبار الـrouting أوفلاين (parse + فحص الصلاحية).
__all__ = [
    "HISTORY_MAX_MESSAGES",
    "RETRIEVAL_RELEVANCE_THRESHOLD",
    "check_permission",
    "decide_category",
    "load_history",
    "parse_decided_category",
    "respond",
    "retrieve",
    "route_after_permission",
    "route_after_retrieve",
]
