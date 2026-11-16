"""GET /conversations و GET /conversations/{id} — تاريخ المحادثات للـsidebar (PRD 10.3).

الـuser_id بيجي من الـJWT المتحقق منه (app/auth/dependencies.py) — مش من
الـclient — فكل موظف شايف محادثاته هو بس.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import AuthenticatedUser, get_current_user
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
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[ConversationSummary]:
    """محادثات الموظف الحالي، الأحدث الأول."""
    return list_conversations(user.user_id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ConversationDetail:
    """
    المحادثة بكل رسايلها بالترتيب الزمني.

    الـownership بيتحقق هنا كمان عشان موظف مايقدرش يفتح محادثة حد تاني بالـid
    بتاعها. 404 سواء المحادثة مش موجودة أو بتاعة حد تاني (مانكشفش إنها موجودة).
    """
    conversation = find_conversation(conversation_id, user.user_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة مش موجودة.")
    return ConversationDetail(
        **conversation.model_dump(), messages=list_messages(conversation_id)
    )
