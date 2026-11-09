"""
قراية وكتابة المحادثات والرسايل (conversations / messages) بـSQL مباشر على session.py.

كل دالة بتفتح transaction لوحدها وبتعمل commit في الآخر (sessionmaker.begin()).
"""

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_session_factory


class ConversationSummary(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime


class StoredMessage(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[dict]
    created_at: datetime


def list_conversations(user_id: UUID) -> list[ConversationSummary]:
    """محادثات الموظف، الأحدث الأول (PRD 10.3)."""
    with get_session_factory().begin() as session:
        rows = session.execute(
            text(
                "SELECT id, title, created_at FROM public.conversations "
                "WHERE user_id = :user_id ORDER BY created_at DESC"
            ),
            {"user_id": user_id},
        ).mappings()
        return [ConversationSummary(**row) for row in rows]


def find_conversation(conversation_id: UUID, user_id: UUID) -> ConversationSummary | None:
    """المحادثة لو موجودة **وبتاعة الموظف ده** — غير كده None (من غير ما نفرّق بين الحالتين)."""
    with get_session_factory().begin() as session:
        row = session.execute(
            text(
                "SELECT id, title, created_at FROM public.conversations "
                "WHERE id = :conversation_id AND user_id = :user_id"
            ),
            {"conversation_id": conversation_id, "user_id": user_id},
        ).mappings().one_or_none()
        return ConversationSummary(**row) if row else None


def list_messages(conversation_id: UUID) -> list[StoredMessage]:
    """رسايل المحادثة بالترتيب الزمني."""
    with get_session_factory().begin() as session:
        rows = session.execute(
            text(
                "SELECT id, role, content, sources, created_at FROM public.messages "
                "WHERE conversation_id = :conversation_id ORDER BY created_at"
            ),
            {"conversation_id": conversation_id},
        ).mappings()
        return [StoredMessage(**row) for row in rows]


def create_conversation(user_id: UUID, title: str) -> UUID:
    """
    ينشئ محادثة جديدة ويرجّع الـid بتاعها.

    Raises:
        sqlalchemy.exc.IntegrityError: الـuser_id مش موجود في profiles (foreign key).
    """
    with get_session_factory().begin() as session:
        return session.execute(
            text(
                "INSERT INTO public.conversations (user_id, title) "
                "VALUES (:user_id, :title) RETURNING id"
            ),
            {"user_id": user_id, "title": title},
        ).scalar_one()


def add_message(
    conversation_id: UUID,
    role: Literal["user", "assistant"],
    content: str,
    sources: list[dict],
) -> None:
    """يضيف رسالة للمحادثة. sources بتتخزن jsonb (فاضية لرسايل الـuser)."""
    with get_session_factory().begin() as session:
        session.execute(
            text(
                "INSERT INTO public.messages (conversation_id, role, content, sources) "
                "VALUES (:conversation_id, :role, :content, CAST(:sources AS jsonb))"
            ),
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "sources": json.dumps(sources, ensure_ascii=False),
            },
        )
