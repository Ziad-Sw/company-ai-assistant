"""
FastAPI dependencies للمصادقة (Tech-Stack.md قسم 6 — القرارات الخمسة المعتمدة).

- get_current_user: Bearer token → التحقق من الـJWT (verification.py) → الـuser_id
  بيتاخد من الـ**sub** claim الموقّع (مش من أي حقل من الـclient) → الـrole
  وfull_name بيتقروا من جدول `profiles` **على السيرفر** — الـrole مش بيتوثق
  منه أبداً من الـtoken payload ولا من أي input خارجي.
- require_admin: 403 غير كده — بيُستخدم في dependencies الـendpoints الإدارية.

الـendpoints بتفتح transaction واحدة للقراية (get_session_factory().begin())
وFastAPI بيشغّل sync dependencies جوه threadpool تلقائياً.
"""

import logging
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text

from app.auth.verification import verify_supabase_jwt
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)

# auto_error=False عشان نرجّع 401 برسالتنا وWWW-Authenticate، مش 403 الافتراضية بتاعة FastAPI.
_bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token")

_INVALID_TOKEN_MESSAGE = "الجلسة مش صالحة — سجّل دخولك تاني."
_NOT_PROVISIONED_MESSAGE = "الحساب ده مش مربوط بصفة موظف — كلم الـadmin."
_ADMIN_ONLY_MESSAGE = "الصفحة دي للـadmin بس."

_PROFILE_SQL = text("SELECT role, full_name FROM public.profiles WHERE id = :user_id")


class AuthenticatedUser(BaseModel):
    """هوية الموظف المتحقق منها — بس اللي الـendpoints مسموح يبنيوا عليها."""

    user_id: UUID
    role: str
    full_name: str


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthenticatedUser:
    """الـBearer token المتحقق منه → user_id من الـtoken + role/full_name من profiles."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_TOKEN_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = verify_supabase_jwt(credentials.credentials)
        user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        # بنسجل نوع الفشل بس — الـtoken نفسه عمره ما بيتسجل في اللوج.
        logger.warning("JWT verification failed: %r", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_TOKEN_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    with get_session_factory().begin() as session:
        row = session.execute(_PROFILE_SQL, {"user_id": user_id}).mappings().one_or_none()
    if row is None:
        # المستخدم موجود في auth.users بس مالوش row في profiles — مش موظف متسجل.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=_NOT_PROVISIONED_MESSAGE
        )
    return AuthenticatedUser(user_id=user_id, role=row["role"], full_name=row["full_name"])


def require_admin(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """403 غير الـadmin — بوابات الـendpoints الإدارية (Phase 3)."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=_ADMIN_ONLY_MESSAGE
        )
    return user
