"""
Endpoints إدارة الموظفين (Phase 3 — PRD 10.6) — للـadmin بس عبر require_admin.

- GET: قائمة الموظفين من profiles + الإيميل مدموج من auth.users عبر admin API
  (الإيميل عايش في auth.users بس — employee_store مش بيلمسه).
- POST: إنشاء موظف — الـadmin بيكتب الـemail local-part (الأسامي العربية مش
  صالحة كإيميل فمفيش توليد تلقائي منها — قرار 2026-11-17) + الاسم + الـrole.
  السيرفر بيولّد password مؤقت قوي ويرجّعه **مرة واحدة** في الـresponse —
  مش بيتخزن صريح في أي حتة (hash بس جوه auth.users) ولا بيتسجل في اللوج.

الفشل بعد إنشاء حساب الـAuth (مثلاً insert الـprofile) بيمسح حساب الـAuth
تاني (compensating delete) — مفيش حسابات يتيمة من غير profile.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client
from supabase_auth.errors import AuthApiError
from supabase_auth.types import User

from app.auth.dependencies import AuthenticatedUser, require_admin
from app.db import audit_store
from app.db.employee_store import EmployeeRow, list_employees
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/employees", tags=["admin-employees"])

EMAIL_DOMAIN = "reelestate.demo"

# local-part: حروف لاتينية صغيرة/أرقام/نقطة/شرطة/شرطة سفلية — 2..64 حرف، مبيبدأش
# ومانتهيش بعلامة. الـfull URL بيبقى f"{local}@{EMAIL_DOMAIN}".
_EMAIL_LOCAL_PATTERN = r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])$"

_NOT_UNIQUE_MESSAGE = "الإيميل ده مستخدم بالفعل — اختار local-part تاني."
_AUTH_FAILED_MESSAGE = "فشل إنشاء حساب الـAuth — جرب تاني."
_PROFILE_FAILED_MESSAGE = "اتعمل حساب الـAuth بس فشل ربطه بصف الموظف — التغييرات اترجعت، جرب تاني."


class EmployeeSummary(BaseModel):
    id: UUID
    full_name: str
    role: str
    email: str | None
    created_at: datetime


class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["sales", "hr", "admin"]
    email_local: str = Field(pattern=_EMAIL_LOCAL_PATTERN)


class EmployeeCredentials(BaseModel):
    """الكريدنشيالز المؤقتة — بتظهر مرة واحدة في الـresponse دي بس."""

    id: UUID
    email: str
    full_name: str
    role: str
    temp_password: str


def _iter_auth_users(sb: Client):
    """كل مستخدمي auth.users صفحة صفحة (نفس نمط seed_demo_accounts — العدد متوقع صغير)."""
    page = 1
    while True:
        users = sb.auth.admin.list_users(page=page, per_page=50)
        yield from users
        if len(users) < 50:
            return
        page += 1


def _find_auth_user_by_email(sb: Client, email: str) -> User | None:
    target = email.lower()
    for user in _iter_auth_users(sb):
        if (user.email or "").lower() == target:
            return user
    return None


def _email_map(sb: Client) -> dict[UUID, str]:
    # supabase-py بيرجّع user.id كنص (مش UUID) — بتحوّل هنا عشان مفتاح الـlookup
    # يتطابق مع employee.id القادم من الداتابيز.
    emails: dict[UUID, str] = {}
    for user in _iter_auth_users(sb):
        if user.email:
            emails[UUID(str(user.id))] = user.email
    return emails


def _generate_temp_password() -> str:
    # ~72 بت عشوائية بصيغة URL-safe — بيتخزن hash بس في auth.users.
    return secrets.token_urlsafe(12)


def _auth_user_deleted_or_raise(sb: Client, user_id: UUID) -> None:
    """compensating delete: لو الـprofile فشل بعد إنشاء الـAuth، الحساب بيتشال
    عشان مفيش user يتيمة مش مربوط بصف موظف (والـaudit مايتسجلش)."""
    try:
        sb.auth.admin.delete_user(str(user_id))
    except AuthApiError:
        logger.exception("فشل مسح حساب الـAuth اليتيم %s", user_id)


@router.get("", response_model=list[EmployeeSummary])
def list_admin_employees(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> list[EmployeeSummary]:
    emails = _email_map(get_supabase())
    return [
        EmployeeSummary(
            id=employee.id,
            full_name=employee.full_name,
            role=employee.role,
            email=emails.get(employee.id),
            created_at=employee.created_at,
        )
        for employee in list_employees()
    ]


@router.post("", response_model=EmployeeCredentials, status_code=status.HTTP_201_CREATED)
def create_employee(
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    payload: EmployeeCreate,
) -> EmployeeCredentials:
    sb = get_supabase()
    email = f"{payload.email_local}@{EMAIL_DOMAIN}"

    # الـadmin API مفيهوش get-by-email — فحص التكرار بلف على الصفحات (رخيص للعدد المتوقع).
    if _find_auth_user_by_email(sb, email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NOT_UNIQUE_MESSAGE)

    temp_password = _generate_temp_password()
    try:
        response = sb.auth.admin.create_user(
            {"email": email, "password": temp_password, "email_confirm": True}
        )
    except AuthApiError as exc:
        # سباق تكرار محتمل لو الـPOST اتعمل مرتين في نفس اللحظة — ندوّر ونحكم.
        if _find_auth_user_by_email(sb, email) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NOT_UNIQUE_MESSAGE) from exc
        logger.exception("إنشاء حساب الـAuth فشل للإيميل %s", email)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=_AUTH_FAILED_MESSAGE) from exc

    user = response.user
    if user is None:  # pragma: no cover — create_user بيرجّع user أو بيطرّي exception
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=_AUTH_FAILED_MESSAGE)

    try:
        sb.table("profiles").insert(
            {"id": str(user.id), "role": payload.role, "full_name": payload.full_name.strip()}
        ).execute()
    except Exception as exc:  # noqa: BLE001 — أي فشل ربط = رجوع كامل (مسح حساب الـAuth)
        logger.exception("ربط الـprofile فشل للموظف الجديد %s", user.id)
        _auth_user_deleted_or_raise(sb, user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=_PROFILE_FAILED_MESSAGE
        ) from exc

    audit_store.record_audit(admin.user_id, "add_employee", "employee", user.id)

    # الـpassword المؤقت بيترجع هنا مرة واحدة — مش بيتسجل في اللوج ولا في أي جدول.
    return EmployeeCredentials(
        id=user.id,
        email=email,
        full_name=payload.full_name.strip(),
        role=payload.role,
        temp_password=temp_password,
    )
