"""
اختبار يدوي لـendpoints إدارة الموظفين (Phase 3) على Supabase الحقيقي.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.test_admin_employees

محتاج قبل التشغيل (السكريبت بيتأكد منهم الأول ويقولك الناقص):
  - SUPABASE_URL وSUPABASE_ANON_KEY وDATABASE_URL في الـ.env
  - حسابات الـdemo (admin وsales وsales... الثلاثة) قابلة لتسجيل الدخول
    (docs/demo-accounts.md)

بيستهلك: صفر — مفيش Gemini ولا OpenRouter. الموظف الاختباري بيتعمل بنفس
الـpattern بتاع سكريبت seed (email_confirm=True) وبيمسح في الآخر من auth.users
(صف الـprofiles بيمسح cascade).
الـexit code: 0 لو كله نجح، 1 لو أي حالة فشلت، 2 لو المتطلبات مش جاهزة.
"""

import os
import sys
import uuid

import httpx
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from scripts.demo_auth import login_all

load_dotenv()

# ملحوظة: demo_auth.EMAIL_DOMAIN بييجي بالـ@ جواه — هنا بنعرّف الدومين من غيره.
EMAIL_DOMAIN = "reelestate.demo"

TEST_LOCAL_PREFIX = "test-employee-"
failures: list[str] = []


def _report(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def missing_preconditions() -> list[str]:
    problems: list[str] = []
    try:
        get_settings()
    except ValidationError:
        problems.append("مفاتيح الـ.env ناقصة في backend/.env")
    try:
        with get_session_factory().begin() as session:
            count = session.execute(text("SELECT count(*) FROM public.profiles")).scalar_one()
        if count < 3:
            problems.append("حسابات الـdemo مش مزروعة — شغّل python -m scripts.seed_demo_accounts الأول")
    except Exception as exc:  # noqa: BLE001 — نفس نمط سكريبت /chat في فحص المتطلبات
        problems.append(f"الداتابيز مش متاحة: {exc!r}")
    return problems


def main() -> int:
    problems = missing_preconditions()
    if problems:
        for problem in problems:
            print(f"⚠️  {problem}")
        return 2

    tokens = login_all(("admin", "sales"))
    from app.main import app  # بعد فحص المتطلبات — الـimport بتاعه fail-fast على الـkeys

    client = TestClient(app)
    admin_headers = {"Authorization": f"Bearer {tokens['admin']}"}
    sales_headers = {"Authorization": f"Bearer {tokens['sales']}"}

    local = f"{TEST_LOCAL_PREFIX}{uuid.uuid4().hex[:10]}"
    email = f"{local}@{EMAIL_DOMAIN}"
    created_user_id: str | None = None

    # ── المصادقة ────────────────────────────────────────────────────────────
    response = client.get("/admin/employees")
    _report("GET بدون token → 401", response.status_code == 401)
    response = client.get("/admin/employees", headers=sales_headers)
    _report("GET بصلاحيات sales → 403", response.status_code == 403)
    response = client.get("/admin/employees", headers=admin_headers)
    _report("GET قائمة الموظفين بالـadmin → 200", response.status_code == 200, response.text)
    if response.status_code == 200:
        emails = {row["email"] for row in response.json()}
        _report(
            "حسابات الـdemo الثلاثة ظاهرة بإيميلاتها",
            emails == {"admin@reelestate.demo", "sales@reelestate.demo", "hr@reelestate.demo"},
            str(emails),
        )

    # ── فشل الإدخال (مش بيلمس auth ولا profiles) ────────────────────────────
    response = client.post(
        "/admin/employees",
        headers=admin_headers,
        json={"full_name": "موظف اختبار", "role": "manager", "email_local": local},
    )
    _report("role غير معروف → 422", response.status_code == 422)
    response = client.post(
        "/admin/employees",
        headers=admin_headers,
        json={"full_name": "موظف اختبار", "role": "sales", "email_local": "غير صالح!"},
    )
    _report("email local غير صالح → 422", response.status_code == 422)
    response = client.post(
        "/admin/employees",
        headers=admin_headers,
        json={"full_name": "موظف اختبار", "role": "sales", "email_local": "admin"},
    )
    _report("إيميل demo محجوز → 409", response.status_code == 409)

    # ── الإضافة السعيدة + الكريدنشيالز بتشتغل فعلاً ──────────────────────────
    response = client.post(
        "/admin/employees",
        headers=admin_headers,
        json={"full_name": "موظف اختبار مؤقت", "role": "sales", "email_local": local},
    )
    _report("إضافة موظف → 201", response.status_code == 201, response.text)
    if response.status_code != 201:
        return 1

    credentials = response.json()
    created_user_id = credentials["id"]
    _report("الكريدنشيالز راجعة كاملة", bool(credentials.get("temp_password")) and credentials["email"] == email, str(credentials))

    login_response = httpx.post(
        f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1/token?grant_type=password",
        headers={"apikey": os.environ["SUPABASE_ANON_KEY"], "Content-Type": "application/json"},
        json={"email": email, "password": credentials["temp_password"]},
    )
    _report("تسجيل دخول بالكريدنشيالز المؤقتة → 200", login_response.status_code == 200)

    # الموظف الجديد ظاهر في القائمة
    response = client.get("/admin/employees", headers=admin_headers)
    listed = any(row["email"] == email for row in response.json())
    _report("الموظف الجديد ظهر في القائمة", listed)

    # ── التنضيف: مسح حساب الـauth (profiles بيمسح cascade) — النجاح = مفيش exception ──
    if created_user_id:
        from app.db.supabase_client import get_supabase

        try:
            get_supabase().auth.admin.delete_user(created_user_id)
            _report("تنضيف الموظف الاختباري", True)
        except Exception as exc:  # noqa: BLE001 — التنضيف بيعرض فشله من غير ما يكسر السكريبت
            _report("تنضيف الموظف الاختباري", False, repr(exc))
        response = client.get("/admin/employees", headers=admin_headers)
        _report("الموظف الاختباري اختفى من القائمة", all(row["email"] != email for row in response.json()))

    print()
    if failures:
        print(f"❌ فشل {len(failures)} اختبار: {', '.join(failures)}")
        return 1
    print("✅ كل اختبارات الموظفين نجحت.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
