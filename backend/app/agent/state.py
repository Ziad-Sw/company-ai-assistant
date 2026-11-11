"""
الـstate المشترك بين nodes الـagent (Tech-Stack.md قسم 5 — structured state، مش نص في الـprompt).

TypedDict بـtotal=False عشان كل node يرجّع تحديث جزئي بالحقول اللي غيّرها بس —
LangGraph بيدمج الـupdates على نفس المفاتيح، فمفيش حاجة تتكتب فوق عن طريق الغلط.

الـrole بيدخل الـstate من أول خطوة كقيمة structured، والـLLM ماليش أي طريق
يعدّلها (الـnodes بتقراها بس). حقول الإدخال (user_id, role, question,
conversation_id, model) بتتحدد مرة واحدة في /chat ومحدش بيعدّلها.
"""

from typing import TypedDict
from uuid import UUID

from app.rag.retrieval import RetrievedChunk


class AgentState(TypedDict, total=False):
    # إدخال — بيتحدد من /chat قبل تشغيل الـgraph
    user_id: UUID
    role: str
    question: str
    conversation_id: UUID | None
    model: str

    # load_history
    history: list[dict[str, str]]  # {"role": "user"|"assistant", "content": ...}

    # decide_category — None = سؤال عام/ملوش category واضحة (بحث في كل scope الـrole)
    decided_category: str | None

    # check_permission
    permission_result: str  # "allowed" | "denied"
    denial_message: str | None

    # retrieve
    retrieved_chunks: list[RetrievedChunk]
    retrieval_ok: bool  # فيه chunks وtop-1 عدّى حد الصلة — غير كده الرد الجاهز "مش لاقي"
