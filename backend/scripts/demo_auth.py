"""
تسجيل دخول حسابات الـdemo عبر Supabase Auth (password grant) لسكريبتات الاختبار.

الكريدنشيالز موثقة في docs/demo-accounts.md، والـaccess_token اللي بيرجّعه بيتبعت
كـAuthorization: Bearer للـendpoints المحمية بعد ما الـrole/user_id بقوا بيتقروا
من الـJWT على السيرفر (مش من الـrequest).
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_ENV = Path(__file__).resolve().parents[1] / ".env"
EMAIL_DOMAIN = "@reelestate.demo"
DEMO_PASSWORD = "Demo@2026!"
VALID_ROLES = frozenset({"sales", "hr", "admin"})


def login(role: str) -> str:
    """الـpassword grant الحقيقي (نفس مسار الـlogin الفعلي) — بيرجّع الـaccess_token."""
    if role not in VALID_ROLES:
        raise ValueError(f"الدور {role!r} مش من أدوار الـdemo المعروفة: {sorted(VALID_ROLES)}")
    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        raise RuntimeError("SUPABASE_URL أو SUPABASE_ANON_KEY فاضيين في backend/.env")
    response = httpx.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json={"email": f"{role}{EMAIL_DOMAIN}", "password": DEMO_PASSWORD},
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"تسجيل الدخول فشل للحساب {role}{EMAIL_DOMAIN}: {response.status_code} — "
            "اتأكد إن حسابات الـdemo متزروعة في Supabase Auth (docs/demo-accounts.md)"
        )
    return response.json()["access_token"]


def login_all(roles: tuple[str, ...]) -> dict[str, str]:
    """tokens جاهزة لكل الأدوار المطلوبة — {'sales': <token>, 'hr': <token>}."""
    return {role: login(role) for role in roles}
