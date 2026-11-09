"""
Seed للـdemo accounts الثلاثة (docs/demo-accounts.md) — auth.users + profiles.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.seed_demo_accounts

بيعمل مستخدم Auth لكل حساب (email_confirm=True — من غير تحقق إيميل) بـservice_role
key عن طريق admin API، وبعدين صف مطابق في profiles بالـrole بتاعه.
السكريبت idempotent: الحساب الموجود بالفعل بيتخطى (لأنه مبيتعملش تاني ومبيضغطش
خطأ)، وصف الـprofiles بتاعه بيتأكد إنه موجود.

البيانات (الإيميلات والباسورد) وهمية بالكامل وموثّقة في docs/demo-accounts.md —
ملف مش secret وممكن يترفع على GitHub (عكس .env). السكريبت بيبص على الملف ده
كمصدر للحقيقة؛ لو اتغير هناك، غيّر الثوابت هنا عشان يفضلوا متطابقين.
الـexit code: 0 لو كله تمام، 1 لو أي حساب فشل.
"""

import sys
from uuid import UUID

from dotenv import load_dotenv
from supabase_auth.errors import AuthApiError
from supabase_auth.types import User

from app.db.supabase_client import get_supabase

load_dotenv()

# المصدر: docs/demo-accounts.md — نفس القيم بالظبط.
DEMO_PASSWORD = "Demo@2026!"
DEMO_ACCOUNTS = [
    {"role": "admin", "email": "admin@reelestate.demo", "full_name": "Admin Demo User"},
    {"role": "sales", "email": "sales@reelestate.demo", "full_name": "Sales Demo User"},
    {"role": "hr", "email": "hr@reelestate.demo", "full_name": "HR Demo User"},
]


def find_auth_user_by_email(sb, email: str) -> User | None:
    """يدوّر على المستخدم بالإيميل في auth.users (الصفحات ورا بعض، 50 في الصفحة)."""
    page = 1
    while True:
        users = sb.auth.admin.list_users(page=page, per_page=50)
        for user in users:
            if (user.email or "").lower() == email.lower():
                return user
        if len(users) < 50:
            return None
        page += 1


def create_auth_user(sb, email: str) -> tuple[User, bool]:
    """
    يعمل مستخدم Auth جديد، ويرجّع (المستخدم، اتعمل جديد ولا لا).

    لو الـcreate فشل (مثلاً سباق مع تشغيل تاني للسكريبت)، بنرجّع ندوّر عليه:
    لقيناه → موجود بالفعل، ملقيناهوش → الفشل حاجة تانية ونرجّعه.
    """
    try:
        response = sb.auth.admin.create_user(
            {"email": email, "password": DEMO_PASSWORD, "email_confirm": True}
        )
        return response.user, True
    except AuthApiError:
        user = find_auth_user_by_email(sb, email)
        if user is None:
            raise
        return user, False


def profile_exists(sb, user_id: UUID) -> bool:
    return bool(
        sb.table("profiles").select("id").eq("id", str(user_id)).execute().data
    )


def ensure_profile(sb, user_id: UUID, role: str, full_name: str) -> None:
    """صف profiles موجود بالفعل بيسيب زي ما هو (مفيش تعديل ولا تكرار)."""
    if not profile_exists(sb, user_id):
        sb.table("profiles").insert(
            {"id": str(user_id), "role": role, "full_name": full_name}
        ).execute()


def seed_account(sb, account: dict) -> str:
    """بيجهز حساب واحد ويرجّع حالته: created / existed (profiles ensured)."""
    existing = find_auth_user_by_email(sb, account["email"])
    if existing is None:
        user, auth_created = create_auth_user(sb, account["email"])
    else:
        user, auth_created = existing, False

    ensure_profile(sb, user.id, account["role"], account["full_name"])
    return "created" if auth_created else "existed (profiles ensured)"


def main() -> int:
    # على Windows، لما الـoutput يتعمله redirect/pipe بيبقى cp1252 وبيقع مع العربي.
    sys.stdout.reconfigure(encoding="utf-8")
    sb = get_supabase()

    results: list[tuple[str, str]] = []
    failures = 0
    for account in DEMO_ACCOUNTS:
        try:
            status = seed_account(sb, account)
            results.append((account["email"], status))
        except Exception as exc:  # noqa: BLE001 — نكمل الباقي ونرجّع exit 1 في الآخر
            failures += 1
            results.append((account["email"], f"FAILED: {exc!r}"))

    print("\n=== ملخص الـseed ===")
    for email, status in results:
        print(f"  {email:30s} → {status}")
    if failures:
        print(f"\n{failures} حساب فشل — شغّل السكريبت تاني (idempotent).")
        return 1
    print("\nجاهز — تسجيل الدخول بالإيميل والباسورد من docs/demo-accounts.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
