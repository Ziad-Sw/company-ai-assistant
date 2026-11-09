"""GET /conversations و GET /conversations/{id} — تاريخ المحادثات للـsidebar (PRD 10.3)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db.conversation_store import (
    ConversationSummary,
    StoredMessage,
    find_conversation,
    list_conversations,
    list_messages,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage]


@router.get("", response_model=list[ConversationSummary])
def get_conversations(
    # TEMPORARY: replace with JWT-derived role/user_id once auth is built
    user_id: UUID,
) -> list[ConversationSummary]:
    """محادثات الموظف، الأحدث الأول."""
    return list_conversations(user_id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    # TEMPORARY: replace with JWT-derived role/user_id once auth is built
    user_id: UUID,
) -> ConversationDetail:
    """
    المحادثة بكل رسايلها بالترتيب الزمني.

    user_id مطلوب هنا كمان عشان موظف مايقدرش يفتح محادثة حد تاني بالـid بتاعها.
    404 سواء المحادثة مش موجودة أو بتاعة حد تاني (مانكشفش إنها موجودة).
    """
    conversation = find_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة مش موجودة.")
    return ConversationDetail(
        **conversation.model_dump(), messages=list_messages(conversation_id)
    )
