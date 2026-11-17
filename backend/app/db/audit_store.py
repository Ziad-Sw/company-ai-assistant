"""
سجل الـaudit_logs (migrations/003) — مين عمل إيه وإمتى على أي مستند/موظف.

الـactor_id ممكن يبقى NULL بعدين لو صف الـprofile اتمسح — الاسم بيرجع LEFT JOIN
عشان الـسجل نفسه يفضل موجود (سجل الحذف لازم يفضل بعد ما الـtarget يتمسح:
PRD 10.5-د، والـtarget_id من غير FK في الـschema عمداً).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_session_factory

__all__ = ["AuditEntry", "list_target_audit", "record_audit"]

_ACTIONS = frozenset(
    {"upload", "edit", "replace", "deactivate", "activate", "delete", "reprocess", "add_employee"}
)
_TARGET_TYPES = frozenset({"document", "employee"})


class AuditEntry(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_name: str | None
    action: str
    target_type: str
    target_id: UUID
    created_at: datetime


def record_audit(actor_id: UUID | None, action: str, target_type: str, target_id: UUID) -> None:
    """يكتب صف واحد في السجل — الـaction/target_type قيمهم قادمة من كود التطبيق
    (متحقق منها ضد الـfrozenset هنا — defense in depth ضد الـCHECK في الـschema)."""
    if action not in _ACTIONS:
        raise ValueError(f"action مش معروفة: {action}")
    if target_type not in _TARGET_TYPES:
        raise ValueError(f"target_type مش معروفة: {target_type}")

    with get_session_factory().begin() as session:
        session.execute(
            text(
                """
                INSERT INTO public.audit_logs (actor_id, action, target_type, target_id)
                VALUES (:actor_id, :action, :target_type, :target_id)
                """
            ),
            {
                "actor_id": actor_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
            },
        )


def list_target_audit(target_type: str, target_id: UUID) -> list[AuditEntry]:
    """سجل target واحد، الأحدث أولاً — مع اسم الـactor لو الـprofile لسه موجود."""
    if target_type not in _TARGET_TYPES:
        raise ValueError(f"target_type مش معروفة: {target_type}")

    with get_session_factory().begin() as session:
        rows = session.execute(
            text(
                """
                SELECT a.id, a.actor_id, p.full_name AS actor_name,
                       a.action, a.target_type, a.target_id, a.created_at
                FROM public.audit_logs a
                LEFT JOIN public.profiles p ON p.id = a.actor_id
                WHERE a.target_type = :target_type AND a.target_id = :target_id
                ORDER BY a.created_at DESC
                """
            ),
            {"target_type": target_type, "target_id": target_id},
        ).mappings()
        entries = [
            AuditEntry(
                id=row["id"],
                actor_id=row["actor_id"],
                actor_name=row["actor_name"],
                action=row["action"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    return entries
