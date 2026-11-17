"""
قراية صفوف الموظفين من public.profiles (نفس نمط document_store — bind params).

الإيميل **مش هنا**: عايش في auth.users بس (schema.sql قسم 2 — profiles مفيهوش
عمود إيميل بالتصميم)، فدمجه بيه بيحصل في طبقة الـAPI عبر admin API بتاع Supabase.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_session_factory

__all__ = ["EmployeeRow", "list_employees"]


class EmployeeRow(BaseModel):
    id: UUID
    full_name: str
    role: str
    created_at: datetime


_LIST_SQL = text(
    """
    SELECT id, full_name, role, created_at
    FROM public.profiles
    ORDER BY created_at ASC
    """
)


def list_employees() -> list[EmployeeRow]:
    with get_session_factory().begin() as session:
        rows = session.execute(_LIST_SQL).mappings()
        employees = [
            EmployeeRow(
                id=row["id"],
                full_name=row["full_name"],
                role=row["role"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    return employees
