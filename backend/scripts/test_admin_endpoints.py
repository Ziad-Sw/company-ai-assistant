"""
اختبار يدوي لـendpoints إدارة المستندات (Phase 3) على Supabase الحقيقي.

طريقة التشغيل (من فولدر backend/، والـvenv مفعّلة):
    python -m scripts.test_admin_endpoints

محتاج قبل التشغيل (السكريبت بيتأكد منهم الأول ويقولك الناقص):
  - SUPABASE_URL وSUPABASE_ANON_KEY وGEMINI_API_KEY وDATABASE_URL في الـ.env
  - migrations/003_admin_phase.sql متطبّقة (audit_logs + حالات processing/failed)
  - storage bucket باسم documents موجود (جزء من migrations/003)
  - حسابات الـdemo (admin وsales) قابلة لتسجيل الدخول (docs/demo-accounts.md)

بيستهلك: نداءات Gemini embedding بس (2-3 chunks لكل ملف اختبار صغير) —
مفيش أي استهلاك لـOpenRouter/chat. المستندات الاختبارية (بادئة test-admin-)
بتتمسح في الآخر من على الـDB والـStorage.
الـexit code: 0 لو كله نجح، 1 لو أي حالة فشلت، 2 لو المتطلبات مش جاهزة.
"""

import sys
import time
from uuid import uuid4

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from scripts.demo_auth import login_all

load_dotenv()

# الرفع/الاستبدال بيشتغلوا بالـBackgroundTasks — المعالجة الحقيقية (embedding +
# كتابة chunks) ممكن تاخد ثواني على Gemini المجاني، فالـpolling بياخد مهلة سخية.
PROCESSING_TIMEOUT_SECONDS = 90
POLL_INTERVAL_SECONDS = 1.5

# محتوى اختبار صغير (chunk واحد تقريباً) — أقل استهلاك ممكن للـembedding.
TEST_BODY = """---
doc_id: {doc_id}
title: مستند اختبار إداري
version: 2026.1
language: ar
---

# سياسة اختبار
هذا محتوى اختبار للتحقق من مسار الرفع والمعالجة. نسبة الدفعة المقدمة 20%.
"""

TEST_BODY_V2 = """---
doc_id: {doc_id}
title: مستند اختبار إداري
version: 2026.2
---

# سياسة اختبار محدثة
هذا محتوى اختبار للنسخة الجديدة. نسبة الدفعة المقدمة 25%.
"""

TEST_BODY_NO_FRONTMATTER = "# ملف من غير frontmatter\nمحتوى بسيط.\n"

created_document_ids: list[str] = []
failures: list[str] = []


def _report(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def migration_ready() -> bool:
    """التحقق من تطبيق migrations/003 قبل أي اختبار — بدونهم الـAPI هيطلع 500s غامضة."""
    try:
        with get_session_factory().begin() as session:
            audit_table = session.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'audit_logs'"
                )
            ).scalar_one_or_none()
            status_check = session.execute(
                text(
                    "SELECT 1 FROM pg_constraint WHERE conname = 'documents_status_check' "
                    "AND pg_get_constraintdef(oid) LIKE '%processing%'"
                )
            ).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 — نفس نمط سكريبت /chat في فحص المتطلبات
        print(f"❌ الداتابيز مش متاحة: {exc!r}")
        return False
    return audit_table is not None and status_check is not None


def missing_preconditions() -> list[str]:
    problems: list[str] = []
    try:
        get_settings()
    except ValidationError:
        problems.append("OPENROUTER_API_KEY أو مفاتيح الـ.env ناقصة في backend/.env")
    if not migration_ready():
        problems.append("migrations/003_admin_phase.sql مش متطبّقة (audit_logs أو حالات processing ناقصة)")
    return problems


def wait_until_processed(client: TestClient, document_id: str, headers: dict[str, str]) -> dict:
    """poll لحد ما الحالة تخرج من processing — بيعرض آخر حالة وصلها أو يفشل بالمهلة."""
    deadline = time.monotonic() + PROCESSING_TIMEOUT_SECONDS
    last_status = "processing"
    while time.monotonic() < deadline:
        response = client.get(f"/admin/documents/{document_id}", headers=headers)
        if response.status_code != 200:
            raise AssertionError(f"الـpoll فشل: {response.status_code} {response.text}")
        last_status = response.json()["status"]
        if last_status != "processing":
            return response.json()
        time.sleep(POLL_INTERVAL_SECONDS)
    raise AssertionError(f"المستند فضل processing أكتر من {PROCESSING_TIMEOUT_SECONDS} ثانية (آخر حالة: {last_status})")


def cleanup(headers: dict[str, str]) -> None:
    for document_id in list(created_document_ids):
        response = client.delete(f"/admin/documents/{document_id}", headers=headers)
        if response.status_code not in (204, 404):
            print(f"⚠️  التنضيف فشل للمستند {document_id}: {response.status_code}")
        created_document_ids.remove(document_id)


def main() -> int:
    global client
    problems = missing_preconditions()
    if problems:
        for problem in problems:
            print(f"⚠️  {problem}")
        return 2

    tokens = login_all(("admin", "sales"))
    client = TestClient(__import__("app.main", fromlist=["app"]).app)

    admin_headers = {"Authorization": f"Bearer {tokens['admin']}"}
    sales_headers = {"Authorization": f"Bearer {tokens['sales']}"}
    doc_id = f"test-admin-{uuid4().hex[:12]}"
    test_body = TEST_BODY.format(doc_id=doc_id)
    test_body_v2 = TEST_BODY_V2.format(doc_id=doc_id)

    # ── المصادقة ────────────────────────────────────────────────────────────
    response = client.get("/admin/documents")
    _report("GET بدون token → 401", response.status_code == 401)
    response = client.get("/admin/documents", headers=sales_headers)
    _report("GET بصلاحيات sales → 403", response.status_code == 403)
    response = client.get("/admin/documents", headers=admin_headers)
    _report("GET قائمة المستندات بالـadmin → 200", response.status_code == 200)

    # ── فشل الرفع (كل الحالات دي ما بتستهلكش embedding) ─────────────────────
    response = client.post(
        "/admin/documents",
        headers=admin_headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"category": "payment_policies"},
    )
    _report("رفع ملف غير Markdown → 422", response.status_code == 422)
    response = client.post(
        "/admin/documents",
        headers=admin_headers,
        files={"file": ("no-frontmatter.md", TEST_BODY_NO_FRONTMATTER.encode(), "text/markdown")},
        data={"category": "payment_policies"},
    )
    _report("رفع ملف بلا frontmatter → 422", response.status_code == 422)
    response = client.post(
        "/admin/documents",
        headers=admin_headers,
        files={"file": ("policy.md", test_body.encode(), "text/markdown")},
        data={"category": "not_a_category"},
    )
    _report("رفع بـcategory غير معروفة → 422", response.status_code == 422)
    response = client.post(
        "/admin/documents",
        headers=admin_headers,
        files={"file": ("policy.md", test_body.encode(), "text/markdown")},
        data={"category": "payment_policies"},
    )
    _report("رفع مستند صالح → 201", response.status_code == 201, response.text)
    if response.status_code != 201:
        return 1

    document = response.json()
    document_id = document["id"]
    created_document_ids.append(document_id)
    processed = wait_until_processed(client, document_id, admin_headers)
    _report("المعالجة خلصت → active", processed["status"] == "active", str(processed))
    _report("اسم الـuploader ظاهر", processed.get("uploaded_by_name") is not None, str(processed))

    # ── تضارب النسخ ─────────────────────────────────────────────────────────
    response = client.post(
        "/admin/documents",
        headers=admin_headers,
        files={"file": ("policy.md", test_body.encode(), "text/markdown")},
        data={"category": "payment_policies"},
    )
    _report("رفع نفس doc_id+version تاني → 409", response.status_code == 409)

    # ── تعديل الـcategory والحالة ────────────────────────────────────────────
    response = client.patch(
        f"/admin/documents/{document_id}",
        headers=admin_headers,
        json={"category": "property_listings"},
    )
    _report("PATCH category → 200", response.status_code == 200 and response.json()["category"] == "property_listings", response.text)
    response = client.patch(
        f"/admin/documents/{document_id}",
        headers=admin_headers,
        json={"status": "inactive"},
    )
    _report("PATCH status → inactive", response.status_code == 200 and response.json()["status"] == "inactive", response.text)
    response = client.patch(f"/admin/documents/{document_id}", headers=admin_headers, json={})
    _report("PATCH فاضي → 422", response.status_code == 422)
    response = client.patch(f"/admin/documents/{uuid4()}", headers=admin_headers, json={"status": "active"})
    _report("PATCH مستند غير موجود → 404", response.status_code == 404)

    # ── الاستبدال: نسخة جديدة، القديمة بتتفعّل inactive بعد النجاح ───────────
    response = client.post(
        f"/admin/documents/{document_id}/replace",
        headers=admin_headers,
        files={"file": ("policy.md", test_body_v2.encode(), "text/markdown")},
    )
    _report("استبدال بنسخة جديدة → 201", response.status_code == 201, response.text)
    if response.status_code != 201:
        return 1
    new_document_id = response.json()["id"]
    created_document_ids.append(new_document_id)
    processed_v2 = wait_until_processed(client, new_document_id, admin_headers)
    _report("النسخة الجديدة → active", processed_v2["status"] == "active", str(processed_v2))

    response = client.get(f"/admin/documents/{document_id}/versions", headers=admin_headers)
    versions = {row["version"]: row["status"] for row in response.json()}
    _report("النسخة القديمة بقت inactive والجديدة active", versions.get("2026.1") == "inactive" and versions.get("2026.2") == "active", str(versions))

    # ── إعادة المعالجة ──────────────────────────────────────────────────────
    response = client.post(f"/admin/documents/{new_document_id}/reprocess", headers=admin_headers)
    _report("إعادة معالجة → 200", response.status_code == 200, response.text)
    if response.status_code == 200:
        processed_re = wait_until_processed(client, new_document_id, admin_headers)
        _report("إعادة المعالجة خلصت → active", processed_re["status"] == "active", str(processed_re))

    # ── الـaudit ────────────────────────────────────────────────────────────
    response = client.get(f"/admin/documents/{document_id}/audit", headers=admin_headers)
    actions = {row["action"] for row in response.json()}
    expected_actions = {"upload", "edit", "replace", "deactivate"}
    _report("الـaudit فيه عمليات الـPhase 3", expected_actions.issubset(actions), str(actions))

    # ── الحذف + السجل يفضل موجود ────────────────────────────────────────────
    response = client.delete(f"/admin/documents/{document_id}", headers=admin_headers)
    _report("DELETE → 204", response.status_code == 204, response.text)
    if response.status_code == 204:
        created_document_ids.remove(document_id)
    response = client.get(f"/admin/documents/{document_id}", headers=admin_headers)
    _report("GET بعد الحذف → 404", response.status_code == 404)
    response = client.get(f"/admin/documents/{document_id}/audit", headers=admin_headers)
    _report("سجل مستند متمسح لسه متاح → 200", response.status_code == 200 and len(response.json()) > 0, response.text)

    # ── التنضيف ─────────────────────────────────────────────────────────────
    cleanup(admin_headers)
    print()
    if failures:
        print(f"❌ فشل {len(failures)} اختبار: {', '.join(failures)}")
        return 1
    print("✅ كل اختبارات الـadmin نجحت.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
