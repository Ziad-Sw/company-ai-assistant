"""GET /me — هوية الموظف من الـsession المتحقق منها (Tech-Stack.md قسم 2)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import AuthenticatedUser, get_current_user

router = APIRouter(tags=["me"])


class Me(BaseModel):
    user_id: str
    role: str
    full_name: str


@router.get("/me", response_model=Me)
def get_me(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> Me:
    """{user_id, role, full_name} من الـJWT المتحقق منه + profiles (مش من الـclient)."""
    return Me(user_id=str(user.user_id), role=user.role, full_name=user.full_name)
