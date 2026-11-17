# Progress Log — Company AI Assistant

> سجل زمني لكل مهمة اتنفذت على المشروع (حسب `Tech-Stack.md` قسم 12). كل مهمة جديدة = entry جديد تحت، من غير ما نمسح القديم.

---

## [2026-11-17] — Phase 3 (Frontend): صفحة إدارة الموظفين /admin/employees (Task 5) + مراجعة الأكواد السابقة

**تم (بمهارات Tech-Stack قسم 10: code-security + clean-code-guard + ux-writing + web-design-guidelines):**
- **`features/admin-employees/` (feature-local):** `types.ts` (EmployeeSummary/Credentials/Roles + نفس pattern إيميل الـbackend للتحقق المبكر)، `api/employees.ts` (GET/POST)، `hooks/useEmployees.ts` (loading مشتق من null + مفيش setState متزامن في effect؛ بعد الإنشاء الناجح بنجيب القايمة من السيرفر تاني — **ممنوع نصنع created_at محلياً**)، والمكونات: `EmployeesScreen` (نفس هيكل المستندات)، `EmployeeTable` (الاسم/الدور/الإيميل بـdir=ltr/تاريخ الإضافة — مفيش أكشنز صفوف في Phase 3 حسب PRD 10.6)، `AddEmployeeModal` (الاسم + الـrole بـDropdown بوصف كل دور + الـemail local-part بتحقق بنفس regex الـbackend — قرار 2026-11-17: مفيش توليد إيميل من الاسم العربي)، `CredentialsModal` (**الكريدنشيالز مرة واحدة** مع تحذير صريح وأزرار نسخ — زرار النسخ مبيعملش «اتنسخ» لو الـclipboard فشل).
- **الـsidebar:** لينك Admin → Employees (أيقونة UsersIcon جديدة) — Task 6 اكتمل.
- **كل الـcopy في en + ar** تحت `adminEmployees.*` بصيغة واضحة: أزرار بفعل أولاً، أخطاء what→why→how، إميلي states بقيمة + أول خطوة، تنبيه الكريدنشيالز بصيغة محايدة.
- **مراجعة الأكواد السابقة (clean-code-guard review) — ملاحظات وصلحات:**
  - **باج namespace في المودال الجديد:** `roles.*` كانت متلخصة تحت `addModal` والمودال بيقرا بمفاتيح غلط — اتصلحت (و`roleDescriptions` اترفعت جنب `roles` في الملفين).
  - **`admin_documents.py`:** `_resolve_or_422` كانت بترجّع نص مش مستخدم (YAGNI) — بقت بترجّع ParsedDocument بس؛ `_create_replacement_version` كانت 8 params — بقت 5 بـ`_PreparedUpload` (NamedTuple: بايتات + هوية + اسم الملف) وحذف `old_document_id` المكرر (بيساوي target.id دايماً)؛ إعادة المعالجة بقت بتستخدم `Path(...).stem` مباشرة.
  - **`extractors.py`:** الـDOCX كان بياخد الفقرات بس — **الجداول كانت بتضيع** (مخططات السداد غالباً جداول!) — اتضاف استخراج الجداول (خلية بخط فاصل، بعد الفقرات). اتختبر موضعياً: فقرات + جدول طلعوا صح، وملف تالف → رسالة عربي واضحة.
- **التحقق:** compileall + imports green (backend)؛ lint + tsc + build (21 routes، /[locale]/admin/employees متسجلة) green (frontend).

**ملفات اتعملت/اتعدلت:**
- frontend/features/admin-employees/** — جديدة (types/api/hook/4 مكونات)
- frontend/app/[locale]/(admin)/admin/employees/page.tsx — جديدة
- frontend/components/shared/Sidebar.tsx (لينك الموظفين) + ui/icons.tsx (UsersIcon)
- frontend/messages/en.json + ar.json — adminEmployees.* + common.sidebar.adminEmployees
- backend/app/api/admin_documents.py + backend/app/rag/extractors.py — وصلحات المراجعة

**الحالة:** ✅ تم (static gates green). **المتبقي:** walkthrough بصري على المستخدم (uvicorn + تسجيل admin → صفحة الموظفين → إضافة موظف → كريدنشيالز → دخول بالموظف الجديد)، وتشغيل `python -m scripts.test_admin_endpoints` لتحقق الـauto-replace.

---

## [2026-11-17] — Phase 3: Auto-replace للصيغ التلقائية + تطبيع أسماء المتصفح

**المشكلة:** رفع ملف PDF محدّث (بلاحقة تحميل متصفح زي « (1)») كان بينزل **مستند جديد منفصل** بدل نسخة لنفس الهوية — نسختين active بيتلمّوا في الـretrieval.

**تم (قرار 2026-11-17 — طلب المستخدم):**
- **تطبيع الـstem** في `document_from_plain_text`: بلاحقات المتصفح `\s+(\d+)$` بتتشال — «Course (3)» و«Course» نفس الهوية.
- **Auto-replace في `upload_document`:** لو الهوية التلقائية موجودة بالفعل (أحدث صف بنفس doc_id) → الرفع بيتبع مسار الاستبدال: نسخة جديدة بنفس doc_id، القديمة **inactive** لما المعالجة تنجح، audit `replace` على الصف القديم، والـcategory المختارة في المودال هي اللي بتتنفذ. لو الـtarget processing → 409.
- **Refactor:** `_create_replacement_version` مشترك بين الاستبدال الصريح (`/replace`) والـauto-replace (نفس الخطوات بالظبط).
- Markdown مش متأثر (الهوية من الـfrontmatter يدوي — الرفع بنفس doc_id ونسخة جديدة لسه مقصود).
- **سكريبت الاختبار:** حالة جديدة — رفع `handbook.txt` → 201، ثم رفع `handbook (1).txt` → 201 auto-replace بنفس doc_id + النسختين (واحدة active واحدة inactive).
- **التحقق الثابت:** compileall + imports green؛ اختبار موضعي للتطبيع («Course (3)» → «Course»). **التشغيلي:** في الترمينال بتاع المستخدم — `python -m scripts.test_admin_endpoints`.

**ملفات اتعملت/اتعدلت:** backend/app/rag/pipeline.py، backend/app/db/document_store.py (find_latest_document_by_doc_id)، backend/app/api/admin_documents.py، backend/scripts/test_admin_endpoints.py

**الحالة:** ✅ تم (static gates green — التحقق التشغيلي على المستخدم). المستند المكرر الموجود حالياً («Course (1)») محتاج حذف يدوي من الواجهة.

---

## [2026-11-17] — Phase 3: إصلاحات صفحة المستندات + قبول كل الصيغ (قبل Task 5)

**تم:**
- **إصلاح قصّ الـDropdown:** قايمة `ui/Dropdown.tsx` كانت `absolute` فبتتقص جوه حاويات overflow (الجدول/المودال) — بقت **fixed-position** بإحداثيات مقيسة من الزرار نفسه (`position: fixed` بتخرج من قص الأجداد)، فتفتح تحت افتراضياً وفوق لو المساحة تحت مش كفاية، وبتعيد القياس مع الـscroll (بـcapture عشان الـscroll الداخلي مبيعملش bubble) والـresize، بـz-50.
- **إصلاح input الملف:** الـinput الأصلي بقى `sr-only` وزرار مخصص «اختار ملف» مكانه — مكان رسالة المتصفح «No file chosen»، واسم الملف المختار بس بيظهر لما يختار فعلاً.
- **كل الصيغ مدعومة (قرار 2026-11-17):** `.md` + `.pdf` + `.docx` + `.txt` — قبل كده Markdown بس.
  - `requirements.txt`: pypdf==7.1.0 + python-docx==1.2.0 (متثبتين في الـvenv، appended بمحارف مرتبة).
  - `app/rag/extractors.py` (جديد): استخراج موحّد لكل الصيغ — PDF بـpypdf (استيراد lazy جوه الـbranch)، DOCX بـpython-docx (فقرات + جداول + `\n\n` بين البلوكات)، MD/TXT بفك UTF-8. أخطاء واضحة بالعربي: `UnsupportedFormatError` / `ExtractionError` (PDF تالف/DOCX تالف/UTF-8 مش صالح).
  - `app/rag/pipeline.py`: `ParsedDocument.auto_identity` + `document_from_plain_text(stem, text)` — للصيغ غير الـMarkdown: `doc_id`/`title` = اسم الملف من غير الامتداد (العربي زي ما هو، slug للـpaths بس)، `version` = UTC timestamp `%Y.%m.%d.%H%M%S`، `language="mixed"`. الـMarkdown زي ما هو (frontmatter إلزامي).
  - `app/api/admin_documents.py`: `_read_upload` بيرجّع بايتات (تحقق امتداد + حجم)، `_resolve_or_422` بيستخرج ويبني الهوية (.md → parse_markdown_document، الباقي → document_from_plain_text؛ أي خطأ استخراج/تحليل → 422 برسالة المستخرج)، **الاستبدال بيثبّت هوية النسخة القديمة** (`target.doc_id`) لو `auto_identity` مهما اختلف اسم الملف الجديد، و**إعادة المعالجة** بتعيد الاستخراج من المصدر بامتداد الملف المحفوظ (الـUTF-8 hardcoded اتشال).
  - Frontend: `DocumentUploader` بيقبل `.md,.pdf,.docx,.txt` بتحقق امتداد مبكر، و`fileHint`/`fileLabel`/`wrongExtension`/`chooseFile` اتحدثوا في en + ar.
- **سكريبت الاختبار:** حالة «رفع ملف غير Markdown → 422» بقت «رفع ملف بامتداد غير مدعوم (.exe) → 422» — `.txt` بقى رفع صالح.
- **التحقق الثابت:** compileall + imports green (backend)، وlint + tsc + build (18 routes) green (frontend)، واختبار استخراج موضعي: .txt و.docx رجّعوا نص صح، وPDF تالف → `ExtractionError` بالرسالة العربي. **التشغيلي على Supabase** (رفع pdf/docx حقيقي + دورة استبدال): في الترمينال بتاع المستخدم — `python -m scripts.test_admin_endpoints`.

**ملفات اتعملت/اتعدلت:**
- backend/app/rag/extractors.py — جديد | pipeline.py + admin_documents.py — اتعدلوا | backend/requirements.txt
- frontend/components/ui/Dropdown.tsx — قايمة fixed | frontend/features/admin-documents/components/DocumentUploader.tsx
- frontend/messages/en.json + ar.json — مفاتيح الـuploader
- backend/scripts/test_admin_endpoints.py — حالة الـ422

**الحالة:** ✅ تم (static gates green — التحقق التشغيلي على المستخدم).

---

## [2026-11-17] — Phase 3 (Frontend): صفحة إدارة المستندات /admin/documents (Task 4)

**تم:**
- **`features/admin-documents/` (feature-local حسب قسم 9):** `types.ts` (DocumentSummary/AuditEntry/الحالات/الـcategories الثلاثة + حد 20MB)، `api/documents.ts` (نداءات الـ9 endpoints — الرفع/الاستبدال multipart بـFormData من غير Content-Type يدوي)، `hooks/useDocuments.ts` (القايمة + فلترة category وبحث بـdebounce 400ms + الأكشنز كلها + **polling للـprocessing بس** — كل ثانيتين لحد ما الصف يخرج من processing ويتوقف)، والمكونات: `DocumentsScreen` (التجميع)، `DocumentTable` (أعمدة PRD 10.5-أ + عمود أكشنز بأيقونات بـaria-labels — تعطيل كامل لصف processing)، `DocumentFilters`، `CategoryPicker` (wrapper على ui/Dropdown)، `DocumentUploader` (مودال رفع/استبدال بتحقق مبكر: .md + ≤20MB)، `VersionHistoryModal`، `AuditLogPanel`، `StatusBadge` (توكنز: active=success، failed=error، processing=primary+spinner، inactive=محايد).
- **`components/ui/Modal.tsx`:** المودال المشترك من قايمة قسم 9 — Escape/نقر بره للإغلاق، focus على اللوحة، role=dialog. مستخدم في الرفع/التعديل/**تأكيد الحذف الإلزامي** (PRD 10.5-ج)/النسخ/الـaudit.
- **`components/shared/AppShell.tsx`:** هيكل الصفحات (sidebar + drawer الموبايل) اتسحب من (chat)/layout — الـ(chat) و(admin) الاتنين بيستخدموه (بدون تكرار)، ومفاتيح openMenu/showSidebar اتنقلت لـ`common.sidebar`.
- **كل الـcopy في `messages/en.json` + `ar.json` تحت `adminDocuments.*`** (صفر strings ثابتة) — ورسائل رفض الـbackend العربي بتتعرض زي ما هي: `apiJson` في `lib/api/client.ts` اتحسّن يقرا `detail` من جسم الـerror، والـContent-Type مش بيتحط للـFormData.
- **التحقق:** lint + `tsc --noEmit` + `build` (18 routes، /[locale]/admin/documents متسجلة) كلهم green. إصلاحات من الـlint: نمط «مفيش setState متزامن في effect» (جلب بـpromise callbacks + loading مشتق من null + مودالات بـrender مشروط عشان التصفير التلقائي).

**ملفات اتعملت/اتعدلت:**
- frontend/features/admin-documents/** — جديدة (types/api/hook/7 مكونات)
- frontend/components/ui/Modal.tsx + 6 أيقونات في icons.tsx — جداد
- frontend/components/shared/AppShell.tsx — جديدة | (chat)/layout.tsx — بقى wrapper | (admin)/layout.tsx — الحماية + AppShell
- frontend/lib/api/client.ts (FormData + error detail)، frontend/lib/utils.ts (formatDateTime)
- frontend/messages/en.json + ar.json — adminDocuments.* + common.sidebar/modal

**الحالة:** ✅ تم (lint + types + build green). **المتبقي: walkthrough بصري على المستخدم** — uvicorn + `npm run dev` → login admin@reelestate.demo → دورة كاملة رفع→processing→active→استبدال→حذف.

---

## [2026-11-17] — Phase 3 (Backend): إدارة الموظفين (Task 3)

**تم:**
- **`app/db/employee_store.py`:** قراية الموظفين من profiles (SQLAlchemy بـbind params، الأقدم أولاً). الإيميل **مش في profiles** بالتصميم (عايش في auth.users بس) — دمجه بيحصل في طبقة الـAPI.
- **`app/api/admin_employees.py` (2 endpoints):**
  - `GET /admin/employees` — قائمة `{id, full_name, role, email, created_at}` مع دمج الإيميل من auth.users عبر admin API (لف صفحات `list_users` بنفس نمط seed_demo_accounts — العدد المتوقع صغير).
  - `POST /admin/employees` — إضافة موظف (PRD 10.6): الـadmin بيكتب الاسم + الـrole (Literal sales/hr/admin → 422 غير كده) + **الـemail local-part** (قرار معتمد: مفيش توليد تلقائي من الاسم لأن الأسامي العربية مش صالحة كإيميل — الـPRD افترض أسامي لاتينية؛ النمط `^[a-z0-9](...)$` 2..64 حرف) → السيرفر يولّد **password مؤقت** بـ`secrets.token_urlsafe` (~72 بت) → `create_user(email_confirm=True)` → insert profiles → audit `add_employee`. التكرار → **409** (فحص قبل + fallback بعد سباق الـcreate). الفشل بعد إنشاء حساب الـAuth → **compensating delete** (مفيش حسابات يتيمة من غير profile). الكريدنشيالز بتترجع **مرة واحدة** في الـresponse — مش بيتخزنوا صريحين في أي جدول ولا اللوج (hash بس في auth.users)، وفُقدانهم = حساب مش قابل للاسترجاع (إعادة تعيين الباسورد = مرحلة لاحقة).
- **`backend/scripts/test_admin_employees.py`:** نفس النمط (TestClient + demo_auth، exit 0/1/2، فحص مسبقات يشوف الـseed) — مصادقة 401/403، القائمة فيها الـdemo الثلاثة بإيميلاتهم، role/local غير صالحين → 422، إيميل محجوز (admin@) → 409، إضافة → 201 → **الدخول بالكريدنشيالز المؤقتة فعلاً (password grant)** → ظهور في القائمة → تنضيف بمسح حساب auth (profiles cascade). صفر استهلاك LLM.
- **التحقق الثابت:** compileall + imports + OpenAPI (GET/POST /admin/employees متسجلين) green. **والتشغيلي: السكريبت عدّى 15/15 على Supabase الحقيقي** — تصحيحات طلعت من التشغيل: `_email_map` كانت بتحط مفاتيح str (supabase-py بيرجّع user.id كنص) وبتدور بمفتاح UUID فكل الإيميلات كانت بترجع None — اتوحّدت بـ`UUID(str(user.id))`؛ سكريبت الاختبار كان بستورد `EMAIL_DOMAIN` من demo_auth (بالـ@ جواه) فبني إيميل `@@` — بيتعرّف محلياً من غير @؛ فحص التنضيف كان بيقيس `is not None` و`delete_user` بيرجّع None على النجاح — بقى مفيش exception = نجاح.

**ملفات اتعملت/اتعدلت:**
- backend/app/db/employee_store.py، backend/app/api/admin_employees.py — جداد
- backend/app/main.py — راوتر admin_employees
- backend/scripts/test_admin_employees.py — جديدة

**الحالة:** ✅ تم ومتحقق تشغيلياً (15/15 اختبار على Supabase الحقيقية — إنشاء موظف + دخول فعلي بالكريدنشيالز المؤقتة + تنضيف كامل).

---

## [2026-11-17] — Phase 3 (Backend): الأساس + دورة حياة المستندات كاملة (Tasks 1-2)

**تم:**
- **Task 1 — migration 003 (`backend/app/db/migrations/003_admin_phase.sql`):** جدول `audit_logs` (Tech-Stack §3) — من غير FK على `target_id` عمداً عشان سجل الحذف يفضل موجود بعد تمسح المستند (PRD 10.5-د)، + indexes على target وcreated_at؛ توسيع `documents_status_check` لـ`('active','inactive','processing','failed')` (اسم الـconstraint الافتراضي من schema.sql بيتظبط بـdrop+add بنفس الاسم)؛ storage bucket خاص `documents` (غير public، file_size_limit 20MB)؛ RLS: قراية audit_logs للـadmin + بوليسي delete للمستندات للـadmin (كانت ناقصة في 002). كل الـstatements idempotent. **schema.sql اتمرّن زي 001** (audit_logs قسم 8 + الحالات الجديدة) عشان الإعدادات الجديدة اللي بتزروعه من الأول.
- **Task 2a — استخراج `app/rag/pipeline.py`:** المصدر الوحيد لمنطق المعالجة (chunk → embed → استبدال chunks) من ingest.py: `parse_markdown_document` (frontmatter إلزامي doc_id/title/version — 422 برسالة عربية بتسمي الحقول الناقصة؛ الـdoc_id **مش بيتslugify** عشان الـidempotency تبقى مطابقة للقديم)، `process_document`، `replace_chunks`، `slugify_for_path` (لآمن مسارات الـStorage بس)، + exceptions مخصصة (MissingFrontmatterError/EmptyDocumentError). `ALL_CATEGORIES` بيتستورد من `retrieval.py` — النسخة الرابعة المكررة اتمسحت. ingest.py بقى سكريبت رقيق بيمرر للـpipeline (سلوك التجاهل للـcategory غير المعروفة زي ما هو).
- **Task 2b — طبقات الداتا:** `app/db/document_store.py` (Pydantic + bind params بالكامل — قائمة مع فلتر category/search واسم الـuploader بـJOIN profiles، find، create بـstatus processing، set status/category **مع jsonb_set لـmetadata.category في الـchunks** (من غير إعادة embedding)، `deactivate_other_versions` (بتقفل مشكلة 2025.1/2026.1 المزدوجة)، versions، delete)، `app/db/audit_store.py` (record + list بـLEFT JOIN profiles)، `app/db/storage_files.py` (رفع/قراية/مسح best-effort — مسارين: bucket للجديد و`data/` على الديسك للـlegacy).
- **Task 2c — `app/api/admin_documents.py` (9 endpoints):** GET list (?category=&search=) وGET {id} (poll endpoint) وPOST رفع (.md بس، category اختيار يدوي من الفورم حسب PRD 10.5-ب، 201 + BackgroundTask) وPATCH (category/status بس، 409 لو processing) وPOST replace (نسخة جديدة بـdoc_id نفسه — 409 لو doc_id مختلق أو نسخة مكررة؛ الفشل بيسيب القديمة active) وPOST reprocess (نفس الملف من مصدره) وDELETE (204 — chunks cascade، ملف best-effort، السجل بيتكتب بعد المسح) وGET versions وGET audit (**بيشتغل بعد الحذف كمان**: مستند مش موجود + سجل موجود = 200). كل العمليات بتتسجل في audit_logs بالأكشن الصح. حمايات: 401/403 عبر require_admin على مستوى الـrouter، الحجم 20MB، UTF-8، منع التعديل أثناء المعالجة (409)، رفع مكرر doc_id+version → 409 (مش هيبني نسختين active يدخلوا الـretrieval).
- **Task 2d — main.py:** راوتر admin_documents + CORS widened لـPATCH/DELETE.
- **Task 2e — `backend/scripts/test_admin_endpoints.py`:** نفس نمط سكريبت /chat (TestClient + demo_auth، exit codes 0/1/2، فحص مسبقات بيطابق تطبيق migration 003 عبر pg_constraint) — مصادقة 401/403، فشل الرفع الثلاثة، رفع سعيد + polling لحد active، تضارب النسخ 409، PATCH/404s، استبدال (القديمة inactive تلقائياً)، reprocess، الـaudit قبل وبعد الحذف، وتنضيف كامل في الآخر. **بيستهلك embeddings بس** (2-3 chunks لكل ملف اختبار) — صفر استهلاك chat.
- **التحقق التشغيلي:** `scripts/test_admin_endpoints.py` عدّى **23/23** على Supabase الحقيقي (بعد ما الـuser طبّق 003 في SQL Editor) — المصادقة، فشل الرفع، الرفع → processing → active، تضارب النسخ، PATCH، الاستبدال (القديمة inactive تلقائياً)، إعادة المعالجة، الـaudit قبل وبعد الحذف، والحذف. تصحيحات طلعت من التشغيل الفعلي: `_validate_category` كانت بتتحقق من مفاتيح `ROLE_ALLOWED_CATEGORIES` (الأدوار) بدل `ALL_CATEGORIES` (الـcategories) — الرفع الإداري بيقبل أي category معروفة؛ `to_jsonb(:category)` بparam من غير نوع (psycopg "polymorphic type") فاتحول لـ`cast(:category AS text)` — والـ`::text` ممنوعة جنب الـbind في text() (الـlookahead بتاع SQLAlchemy بيرفضها فالبند بيختفي من الـparameters)؛ `DocumentSummary` كانت مش بتحمل `source_path` فإعادة المعالجة كانت بتفشل — اتضاف (هتنفع كمان لعرض اسم الملف في جدول الـUI). `HTTP_422_UNPROCESSABLE_ENTITY` المتقادمة اتبدلت بـ`HTTP_422_UNPROCESSABLE_CONTENT`.

**ملفات اتعملت/اتعدلت:**
- backend/app/db/migrations/003_admin_phase.sql — جديدة (**متطبّقة فعلياً في Supabase**)
- backend/app/db/schema.sql — audit_logs + الحالات الجديدة (مزامنة مع 003)
- backend/app/rag/pipeline.py — جديدة | backend/app/rag/ingest.py — أُعيد كـthin caller
- backend/app/db/document_store.py، audit_store.py، storage_files.py — جديدة
- backend/app/api/admin_documents.py — جديدة | backend/app/main.py — راوتر + CORS
- backend/scripts/test_admin_endpoints.py — جديدة

**الحالة:** ✅ تم ومتحقق تشغيلياً (23/23 اختبار على الداتابيز الحقيقية). ملاحظة: تشغيلات الاختبار الفاشلة السابقة سابت مستندات `test-admin-*` يتيمة في الـDB — هتتمسح من واجهة الـadmin لما تجهز (Task 4).

---

## [2026-11-16] — متابعات الـsidebar: نقل تفضيلات الموظف (theme + language) لأسفل الـpanel (مراجعة المستخدم)

**تم:**
- **المشكلة:** التبويبات الجديدة (theme/language) اتحطت جنب الهوية في هيدر الـsidebar — الاسم بيتقص ("Admin Dem…") عشان يفضل مكان للزرارين، وصف واحد بيحمل 4 عناصر مختلفة الوظيفة (هوية + لغة + مظهر + طي).
- **الترتيب الجديد (نمط Gemini/Claude):** الهيدر رجع للهوية بس (الاسم + الـrole بعرضهم كامل + زرار الطي)، والتفضيلات نزلت في **صف فوق زرار تسجيل الخروج** — عنقود "هوية/تفضيلات" المعروف في أسفل الـsidebar. صف `grid grid-cols-2 gap-2` (بيتقلب صح في الـRTL تلقائياً).
- **التبويبات اتبنت على `Button` المشترك** (variant `secondary` size `sm`) بدل classes يدوية — مطابقة إلزامية للـDesign-System §4 (أي زرار يتسحب من ui/Button)، وشكلها بقى متسق مع زرار "+ New chat" الـsecondary. في صفحة الدخول فضلوا chip في الركن بنفس الستايل.

**ملفات اتعدلت:**
- components/shared/Sidebar.tsx — الهيدر رجع للهوية + الطي، صف التفضيلات في الفوتر فوق تسجيل الخروج
- components/shared/ThemeToggle.tsx، components/shared/LanguageSwitcher.tsx — رندر على ui/Button (secondary/sm) بدل زرار مخصص بـclasses
- app/[locale]/(auth)/login/page.tsx — gap-2 بين الـchips

**الحالة:** ✅ تم — lint + types + build عدّوا. التحقق البصري على المستخدم.

---

## [2026-11-16] — عارض الـmarkdown لردود الـAI (إقفال آخر مخرَج من خطة الـUI)

**تم:**
- `react-markdown@10.1.0` + `remark-gfm@4.0.1` (المكتبتان الوحيدتان الجديدتان في الـfrontend) — عارض `MarkdownContent` في `features/chat/components/` (feature-local حسب قسم 9) بيحوّل رد الـAI لعناصر React بمطابقة توكنز الـDesign-System: فقرات/lists بـ`text-base leading-6` وmarkers بـ`text-muted`، headings بـ`font-semibold`، كود بـ`bg-input` + `overflow-x-auto`، جداول GFM بحدود `border` و`text-start` (RTL-safe)، blockquote بـ`border-s`، links بـ`text-primary` + `hover:text-primary-hover`.
- **الدمج في `MessageBubble` لردود الـAI بس** — رسالة الموظف فضلت نص عادي (`whitespace-pre-wrap`)، و`denied`/`error` زي ما هما. الـstreaming بيشتغل معاه (إعادة parse لكل token — النصوص محدودة بـ`max_tokens=2048`).
- **الأمن (LLM05):** الحماية بالبناء مش بالتنظيف بعد الحدوث — react-markdown بيرندر لعناصر React من غير أي `innerHTML`، الـHTML الخام بيتم تجاهله افتراضياً (مفيش `rehype-raw`)، والـURL transform الافتراضي بيحذف `javascript:` والخطيرة. **الصور ممنوعة عمداً** (`img: () => null`) — مفيش حاجة تفتش URLs من متصفح الموظف (tracking/SSRF من جهة العميل) لأن رد الموديل untrusted. الـlinks الخارجة بـ`target="_blank"` + `rel="noopener noreferrer"`. DOMPurify مش محتاج أصلاً لأن مفيش HTML sink.

**ملفات اتعملت/اتعدلت:**
- frontend/features/chat/components/MarkdownContent.tsx — جديدة
- frontend/features/chat/components/MessageBubble.tsx — استبدال `<p whitespace-pre-wrap>` بـ`<MarkdownContent>` لردود الـAI
- frontend/package.json — `react-markdown` + `remark-gfm`

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- الـheadings h1/h2 من الـmarkdown بتترندر h3 جوه الفقاعة عشان ماتضربش hierarchy الصفحة (عملياً الردود الـgrounded نادراً فيها headings — الـprompt بيطلب prose + citations).
- `npm audit` فيه 7 moderate — كلها **موجودة قبل كده** في dev toolchain (`typescript-eslint` → `minimatch`)، مش من المكتبتين الجداد، وdev-only. اتحست ومتصلحتش (برا نطاق المهمة).
- skill passes: **llm-security (LLM05)** وقت الكتابة (السلوك الافتراضي الآمن اتأكد منه من الـpackage نفسه مش من الذاكرة) ← Clean Code Guard (اتصلح: join يدوي للـclasses اتبدل بـ`cn()` المشروع) ← Web Design Guidelines قبل التسليم.

**الحالة:** ✅ تم statically (lint + types + build). التحقق البصري على رد حقيقي في المتصفح على المستخدم (نفس blocker البيئة الموثق تحت).

---

## [2026-11-16] — الوضع الداكن اليدوي (toggle مخزن في localStorage — الخيار المسموح في Design-System §5)

**تم:**
- **التبديل بقى class-based:** `globals.css` — بلوك `@media (prefers-color-scheme: dark)` اتبدل بـ`html.dark { ... }` بنفس قيم التوكنز بالظبط، و`@custom-variant dark` اتضاف عشان الـ`dark:` utilities تتبع الكلاس مش تفضيل النظام. مفيش أي component اتعدل (كلهم بيستهلكوا التوكنز).
- **سكريبت inline قبل أول paint** في `<head>` بتاع layout الـ`[locale]` — النمط الرسمي من دليل Next 16 (`preventing-flash-before-hydration.md`): بيقرا `localStorage` وإلا `prefers-color-scheme`، مع `suppressHydrationWarning` على `<html>`. **تفضيل النظام هو الـdefault** لما مفيش قيمة مخزنة — يعني بدون تدخل يدوي السلوك زي زمان بالظبط.
- **`ThemeToggle` في `components/shared`**: بيبدّل الكلاس على `<html>` ويحفظ في `localStorage["theme"]`، وأيقونة Sun/Moon جديدين في `components/ui/icons.tsx`. المكانين زي الـlanguage switcher: identity row في الـsidebar + ركن صفحة الدخول.
- **مزامنة الـstate مع الـDOM بـ`useSyncExternalStore`** — الـstore الخارجي هو كلاس `html.dark` والاشتراك بـ`MutationObserver` (attributeFilter: class). مفيش نسخة تانية من الحالة، ومفيش `setState` جوه effects.

**ملفات اتعملت/اتعدلت:**
- frontend/app/globals.css — class-based dark + `@custom-variant`
- frontend/app/[locale]/layout.tsx — سكريبت الـtheme الـinline + `suppressHydrationWarning`
- frontend/components/shared/ThemeToggle.tsx — جديدة
- frontend/components/ui/icons.tsx — SunIcon/MoonIcon
- frontend/components/shared/Sidebar.tsx، app/[locale]/(auth)/login/page.tsx — المواضع
- frontend/messages/{en,ar}.json — `common.toggleTheme` ("Switch theme" / "تبديل المظهر")

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- قاعدة الـlint الجديدة `react-hooks/set-state-in-effect` رفضت أول نسخة (setState جوه effect) — **الحل هيكلي مش تعطيل القاعدة**: `useSyncExternalStore`. الـdev Strict Mode remount (اللي بيمسح الكلاس من `<html>`) اتعالج بـ`useLayoutEffect` بيعيد التطبيق — no-op في الإنتاج (موصى به رسمياً في دليل Next).
- **تكرار مقصود وموثق:** منطق اشتقاق الـtheme موجود مرتين — جوه السكريبت الـinline (لازم vanilla self-contained) وفي `resolveStoredTheme()` — cross-referenced بتعليقات في الطرفين عشان يفضلوا متطابقين.
- `theme-color` في الـviewport فضل media-based — المتصفح بيقراه قبل الـpaint ومفيش طريقة class-driven من غير JS إضافي.
- skill passes: Code Security وقت الكتابة (localStorage للتفضيل بس — مش بيانات حساسة، مفيش أسرار) ← Clean Code Guard ← UX Writing ← Web Design Guidelines (`color-scheme: dark` على `html.dark` يصلح scrollbars/inputs، aria-pressed للحالة، hydration-safe).

**الحالة:** ✅ تم statically (lint + types + build). التحقق البصري (light/dark × en/ar × موبايل) على المستخدم.

---

## [2026-11-16] — مبدّل اللغة en/ar (إقفال مكوّن `LanguageSwitcher` من قسم 9)

**تم:**
- **`components/shared/LanguageSwitcher.tsx`** — زرار بيبدّل بادئة الـlocale في المسار الحالي بنفس الصفحة، بـ`router.replace` مش `push` (زرار الرجوع مايرجعش لنفس الصفحة بلغة تانية). الـlabel الظاهر هو **اسم اللغة الهدف بلغتها هي** ("English" / "العربية" — مع `translate="no"` عشان الترجمة الآلية ماتبوّظهاش)، والـaria-label مترجم (`common.switchLanguage`).
- **`i18n/navigation.ts`** — `createNavigation(routing)` بـexports الـusePathname/useRouter المستخدمين فعلاً بس (الـusePathname بيرجّع المسار من غير البادئة والـrouter بيحطها حسب الـlocale المطلوب).
- **الموضعان:** ركن ثابت `end-4 top-4` في صفحة الدخول (مفيش sidebar فيها واختيار اللغة أهم قبل الدخول)، وidentity row في الـsidebar جنب زرار الطي (متاح في الـdrawer على الموبايل برضه). الـ`dir` والخط بيتقلبوا تلقائي من layout الـ`[locale]`.

**ملفات اتعملت/اتعدلت:**
- frontend/i18n/navigation.ts — جديدة
- frontend/components/shared/LanguageSwitcher.tsx — جديدة
- frontend/components/shared/Sidebar.tsx، app/[locale]/(auth)/login/page.tsx — المواضع
- frontend/messages/{en,ar}.json — `common.switchLanguage`

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- مفيش حفظ إضافي للـlocale — **الـURL نفسه هو مصدر الحقيقة** (deep-linkable)، والـlocale الحالي بيتحدد من المسار.
- مفيش `useSearchParams` — مفيش route في المشروع بستخدم query params حالياً، وتحيدها كان هيفتاح مشكلة Suspense في الـstatic rendering (YAGNI).
- skill passes: Code Security (المسار الهدف من pathname داخلي بس — مفيش open redirect) ← Frontend Design وقت الكتابة (بناء على نمط icon-button الموجود في الـidentity row) ← Clean Code Guard ← UX Writing ← Web Design Guidelines.

**الحالة:** ✅ تم statically (lint + types + build). التحقق البصري على المستخدم.

---

## [2026-11-16] — المرحلة: واجهة الشات الأساسية (شات + sidebar + dropdown الموديلات) — إقفال آخر مخرَج من Phase 1

**تم:**
- **صفحة الشات الكاملة** (`/[locale]/chat`) بديل الـplaceholder: قايمة رسايل بفقاعات حسب الـDesign-System (رسالة الموظف `primary` على الـinline-end وبتتقلب تلقائياً في الـRTL، رد الـAI `bg-surface` بحدود)، مؤشر 3 نقط أثناء انتظار أول token، والرد بيتعرض نص عادي (ممنوع `dangerouslySetInnerHTML` — مخاطرة LLM05 المسجلة). المصادر بتظهر badges صغيرة (اسم المستند + الإصدار) بعد الـ`done`.
- **بروتوكول الـSSE كله مدعوم:** `token`/`done`/`denied`/`error` — الـ`denied` بيعرض مكوّن رفض الصلاحية (أيقونة قفل + `error-subtle`) بالنص بتاع الـbackend حرفياً، والـ`error` ملاحظة خطأ جوه الفقاعة مع الحفاظ على أي tokens جزئية. المحادثة الجديدة بترجع `X-Conversation-Id` والـURL بيتحدّث فوراً لـ`/chat/{id}` (بدون مسح المحتوى اللي قدام المستخدم).
- **sidebar المشترك** (`components/shared/Sidebar.tsx` حسب Tech-Stack قسم 9): ثابت 280px على الديسكتوب وdrawer بـoverlay على الموبايل، زرار "+ New Chat" ثابت فوق، هوية الموظف (الاسم + الـrole من الـauthStore للعرض) + تسجيل خروج، والـpositioning منطقي (`start`) فبيتقلب صح في الـRTL.
- **تاريخ المحادثات:** قايمة المحادثات (الأحدث الأول من GET /conversations) مع المحادثة النشطة بـ`primary-subtle`، empty state وloading وerror لكل حالة، وrefetch عند إضافة محادثة جديدة (عداد `conversationsVersion` في الـchatStore بدل polling). صفحة `/chat/[conversationId]` بتجيب الـhistory من GET /conversations/{id} وبتكمّل رسايل live بنفس الـflow — و404 (مش موجودة/مش بتاعته) بيطلع رسالة وزرار رجوع.
- **اختيار الموديل (PRD 10.4):** generic `Dropdown` في `components/ui` (كيبورد كامل: أسهم/Enter/Escape/نقر بره، `listbox`/`option` + `aria-activedescendant`، علامة ✓ للمختار) و`ModelDropdown` بيغذي منه من GET /models. الموديل اللي اختفى من المجانية: الـ422 من /chat بيرجّع القايمة وينقّي أول متاح تلقائياً مع تنبيه واضح فوق شريط الإدخال والمسودة محفوظة. فشل جلب القايمة أو قايمة فاضية ليهم empty states (إلزامي في الـDesign-System).
- **المدخلات:** `ChatInput` بـtextarea بتكبر، Enter يبعت (مع احترام الـIME العربي)، Shift+Enter سطر جديد، وسقف 4000 حرف مطابق للـbackend. فشل الإرسال قبل الـstream (422/500/شبكة) بيشيل الـplaceholder الفاضي وبيعرض تنبيه — المسودة بتفضل موجودة.
- **الكوبي:** كل النصوص الجديدة في `messages/en.json` و`ar.json` (empty states/errors/loading بـellipsis) — والـplaceholder strings اتشالت مع المكوّن بتاعها.

**ملفات اتعملت/اتعدلت:**
- frontend/features/chat/api/chat.ts، features/chat/api/models.ts، features/conversations/api/conversations.ts — طبقة الـAPI (SSE client مبني على apiFetch الموجود بكل حاجته: Bearer + silent refresh + redirect-on-401، مع AbortController)
- frontend/store/chatStore.ts — جديدة (محادثة نشطة + موديل مختار + عداد الـconversations؛ عرض بس زي الـauthStore)
- frontend/features/chat/hooks/useChat.ts، features/chat/hooks/useModels.ts — دورة حياة المحادثة وحالة الموديلات
- frontend/features/chat/components/{MessageBubble، PermissionDeniedMessage، MessageList، ChatInput، ChatComposer، ModelDropdown}.tsx — الجديدة
- frontend/features/chat/types.ts، frontend/features/conversations/components/{ConversationList، ConversationItem}.tsx — الجديدة
- frontend/components/ui/Dropdown.tsx، frontend/components/shared/Sidebar.tsx — الجديدة (مشتركين حسب قسم 9)
- frontend/app/[locale]/(chat)/layout.tsx — جديدة (الهيكل: sidebar + header موبايل)
- frontend/app/[locale]/(chat)/chat/page.tsx — إعادة كتابة (بديل الـplaceholder)
- frontend/app/[locale]/(chat)/chat/[conversationId]/page.tsx — جديدة
- frontend/features/auth/components/ChatPlaceholder.tsx — اتمسحت
- frontend/messages/{en،ar}.json — نصوص الشات الجديدة
- docs/PROGRESS.md — الـentry ده

**skill passes (ترتيب قسم 10):** Code Security وقت الكتابة (كل النداءات عبر apiFetch، رد الموديل نص فقط، المصادر عرض من داتا الـbackend، الـevents بتتفحص ضد allowlist، مفيش أسرار في الـclient) ← Clean Code Guard بعد كل ملف (اتصلح: `locale` راجعة من useChat بدون استخدام اتشالت، الـcomposer المشترك `ChatComposer` بدل تكرار في الصفحتين، ModelDropdown بقت عرضية بعد ما أول نسخة كانت بـcontext provider مكسور الوصول) ← UX Writing على نصوص الرسايل ← Web Design Guidelines قبل التسليم (listbox/aria-activedescendant للـdropdown، role=log + aria-live للرسايل، focus-visible في كل العناصر، aria-expanded للقوائم، RTL بخصائص منطقية، تباين text-muted على bg-sidebar في dark مطابق لملاحظة الـDesign-System). Test Guard مش مطبق — مفيش ملفات اختبار اتكتبت (مفيش infra اختبارات frontend لسه). مفيش تعديل backend خالص.

**اللي اتجرّب فعلاً:** lint + tsc + `next build` كاملين (الـroutes بتاعة /chat و/chat/[conversationId] بتتولد صح)، و`GET /models` live من الـbackend (15 موديل نصي). **مسار الـstream الكامل ماتجرّبش end-to-end من الجلسة دي بسبب blocker بيئي:** أي عملية بتتشغّل من جلسة الأداة دي بتحترم Application Control policy بترفض DLL بتاع psycopg ("An Application Control policy has blocked this file") فأي endpoint بيلمس الداتابيز بيرجع 500 من العمليات المتولدة هنا — مش عيب كود (نفس الـsetup عدّى اختباراته live يوم 2026-11-14 من الترمينال العادي). **التحقق المطلوب من الترمينال العادي:** `uvicorn app.main:app --reload` من backend/ + `npm run dev` من frontend/ + حساب sales من docs/demo-accounts.md: سؤال تقسيط → streaming + مصادر؛ فتح المحادثة من الـsidebar؛ سؤال وحدات بحساب hr → رسالة رفض؛ عربي/RTL + dark mode + موبايل. (اختياري بالـquota: تجربة 422 بتاع اختفاء الموديل.)

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- **الرد بيتعرض نص عادي مش markdown** — قرار مقصود (نطاق المرحلة): الـgrounded prompt بيرجّع نص مع citations، وعمل markdown renderer آمن (sanitize) مرحلة صغيرة منفصلة لو اتحتاجت. ممنوع `dangerouslySetInnerHTML` (LLM05).
- **بعد أول رد في محادثة جديدة الـURL بيتعمله `router.replace` لـ/chat/{id}** — الصفحة بتعمل remount وتجيب الـhistory من الـbackend (مصدر الحقيقة) بدل نقل الـstate. الـpersist حصل قبل الـ`done` فمفيش race.
- **مصادر الـcitations اللي الموديل ذكرها مش المهمة** — الـbadges بتعرض الـ5 chunks اللي اتبعتت للموديل (نفس اللي محفوظين في messages.sources، الموثق في Phase 1).
- **الـscroll دايماً لآخر رسالة** على كل تحديث — مفيش "stick to bottom" ذكي (مهمة صغيرة لاحقة لو ضاقت الشاشة).
- **الـquota:** الجلسة دي مااستهلكتش أي LLM requests (الـ500 حصل قبل أي نداء OpenRouter — فشل import psycopg الأول).
- ملف pytest لا frontend: اتحسم إن مفيش اختبارات واجهة في المرحلة دي (مفيش runner متسطب) — التحقق lint/tsc/build + E2E يدوي موثق فوق.

**الحالة:** ✅ تم — الواجهة كاملة ومتحقق منها statically (lint + types + build). التشغيل الحي الكامل محتاج خطوة يدوية من الترمينال العادي بسبب blocker بيئي للجلسة (موثق فوق)، ومفيش أي تغيير backend مطلوب.

---

## [2026-11-16] — متابعات واجهة الشات: طي الـsidebar + أيقونات عناصر القايمة (مراجعات المستخدم)

**تم:**
- **إصلاح حجم الأيقونات:** مكوّن الأيقونات كان بيستبدل `size-4` الافتراضي بأي className إضافي (فالقلم اتوسّع يملأ الزرار). الحجم بقى prop صريح (`sm/md/lg`) مالوش تعارض مع classes الستايل.
- **طي/فتح الـsidebar (زي Gemini):** زرار دائري بأيقونة panel+سهم جوه هيدر الـsidebar (ديسكتوب بس) بيطيّي الـpanel — ولما يطيّ زرار دائري صغير ثابت فوق-الـstart في منطقة المحتوى بيعيده. الـstate في layout الـ(chat) (`collapsed` للديسكتوب + `drawerOpen` للموبايل)، والظهور بيتحسب بالـclasses بدون JS media queries. الـicon بينعكس بالـRTL (`rtl:-scale-x-100`).
- **زرار "+ New Chat" بأيقونة +** (بديل القلم بعد المراجعة)، وأيقونة الـlogout بتنعكس RTL برضه.
- **إزالة أيقونة الـbubble المتكررة من عناصر المحادثات** (كانت noise في كل عنصر) — فضلت بس في empty state بتاع المحادثة الجديدة.
- تسجيل الخروج اتقبل من المراجعة السابقة: آخر الـpanel كزرار danger أحمر بعرض كامل.

**ملفات اتعدلت:** components/ui/icons.tsx (PlusIcon + PanelToggleIcon بدل PencilIcon، حجم صريح)، components/shared/Sidebar.tsx، app/[locale]/(chat)/layout.tsx، features/conversations/components/ConversationItem.tsx، app/[locale]/(chat)/chat/page.tsx، messages/{en,ar}.json (collapseSidebar/showSidebar).

**الحالة:** ✅ تم — lint + types + build عدّوا. التحقق البصري في المتصفح على المستخدم.

---

## 2026-11-08 — Prep fixes قبل بناء الـretrieval (ingestion idempotency + requirements)

**تم:**
- خلّينا الـingestion idempotent: قبل ما نكتب الـchunks بتاعة أي مستند، بنمسح الـchunks القديمة اللي ليها نفس `document_id`. قبل كده، الـ`documents` بس كانت بتتعمل upsert، والـchunks كانت بتتعمل `insert` من جديد كل مرة، فتشغيل `python -m app.rag.ingest` مرتين كان بيكرر كل الـchunks ويبوّظ نتائج الـretrieval (نفس النص يرجع أكتر من مرة في الـtop-k).
- المسح بيحصل **بعد** ما الـembeddings تتحسب، مش قبلها: لو Gemini API فشل في نص المستند، الـchunks القديمة تفضل موجودة بدل ما المستند يفضل من غير chunks.
- ضفنا لـ`requirements.txt` المكتبتين اللي كانوا متسطبين في الـvenv ومش متسجلين: `python-frontmatter==1.3.0` و`langchain-text-splitters==1.1.3` (الإصدارات اتأكدت بـ`pip show`). من غيرهم أي تسطيب جديد أو deploy على Railway/Render كان هيقع بـ`ModuleNotFoundError` في `ingest.py` و`chunking.py`.

**ملفات اتعملت/اتعدلت:**
- backend/app/rag/ingest.py — دالة جديدة `replace_chunks()` (مسح chunks المستند + insert الجديدة)، والـdocstring اتحدث
- backend/requirements.txt — إضافة `python-frontmatter` و`langchain-text-splitters` بإصداراتهم المتسطبة
- docs/PROGRESS.md — إنشاء الملف لأول مرة

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- المسح والإضافة **مش atomic** (Supabase Python client مفيهوش transactions). لو الـdelete نجح والـinsert فشل، المستند هيفضل من غير chunks لحد ما السكريبت يتشغل تاني. ده مقبول لسكريبت ingestion بيتشغل يدوي؛ الحل الكامل (لو احتجناه وقت الـDocument Management في Phase 3) هو Postgres function (RPC) تعمل الاتنين في transaction واحدة.
- `requirements.txt` متخزن بـencoding **UTF-16 LE** (غالباً من `pip freeze >` في PowerShell 5)، وعشان كده git بيعتبره binary ومش بيعرض diff. pip بيقراه عادي، لكن يُفضل تحويله لـUTF-8 في مهمة منفصلة. الـencoding متغيّرش في المهمة دي.
- لسه مش متحل (برا نطاق المهمة): نسختين `payment_policies` (2025.1 و2026.1) الاتنين `status = active`، فالـretrieval هيرجّع أرقام السياسة القديمة جنب الجديدة. لازم يتحل قبل أو مع بناء `retrieval.py`.

**الحالة:** ✅ تم

---

## 2026-11-08 — Phase 1: Permission-aware retrieval

**تم:**
- اتصال SQLAlchemy مباشر بـPostgres (psycopg 3) — لأن PostgREST مايقدرش يعمل `<=>` من غير RPC function.
- `retrieve_chunks(query, role, category=None, top_k=5)`: فحص صلاحية deterministic → `embed_query()` (الـquery-side embedding) → بحث cosine بـpgvector على `chunks JOIN documents` مفلتر بـ`category = ANY(:categories)` → `RetrievedChunk` (Pydantic).
- الصلاحيات: `ROLE_ALLOWED_CATEGORIES` (sales/admin: الـ3، hr: `company_info_support` بس). category مش مسموحة → `PermissionDeniedError` برسالة بتسمّي الـrole والـcategory والمسموح. من غير category → البحث في كل المسموح للـrole.
- سكريبت اختبار يدوي بـ3 حالات بيطبع النتايج وبيرجّع exit code 1 لو أي حالة فشلت.
- اتأكدنا من منطق الصلاحيات offline (كل الفروع)، ومن الـmapping لـ`RetrievedChunk`، ومن ترتيب النتايج الفعلي بحساب نفس الـcosine في Python على الـembeddings الحقيقية من Supabase: سؤال الفيلا بحديقة → Mountain View #1 (0.679)؛ سؤال خطط التقسيط → نسخة 2026.1 (0.792) و2025.1 (0.787) في المركز الأول والتاني.

**ملفات اتعملت/اتعدلت:**
- backend/app/db/session.py — engine + sessionmaker (lazy، من `DATABASE_URL`)، SSL إلزامي، pre_ping، وprepared statements مقفولة عشان الـpooler
- backend/app/rag/retrieval.py — `RetrievedChunk`, `ChunkMetadata`, `PermissionDeniedError`, `ROLE_ALLOWED_CATEGORIES`, `resolve_categories()`, `retrieve_chunks()`
- backend/scripts/test_retrieval.py — 3 حالات (sales/listings، hr/listings مرفوض، sales/payment بالنسختين)؛ التشغيل: `python -m scripts.test_retrieval`
- backend/.env.example — إضافة `DATABASE_URL` (placeholder فاضي + مصدره في Supabase)

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- ⚠️ **`DATABASE_URL` مش موجود في الـ`.env`** — السكريبت ماتشغّلش end-to-end على الداتابيز لسه. لازم يتضاف من Supabase → Connect → Session pooler، وبعدها `python -m scripts.test_retrieval`.
- `similarity_score = 1 - cosine_distance` (range [-1, 1]، الأعلى = أقرب) — موثّق في comment جوه `RetrievedChunk`.
- `metadata` اتعمل Pydantic model (`ChunkMetadata`) بدل `dict` خام — نفس المفاتيح المطلوبة (section, page, version, updated_at, language)، بس typed و`model_dump()` بيرجّعه dict.
- `page` دايماً `None` حالياً (المصدر Markdown)؛ `section` ممكن يبقى `{}` لنص قبل أول `##`.
- `metadata.updated_at` جاي من `documents.updated_at` = **وقت الـingestion**، مش `updated_at` بتاع الـfrontmatter (ingest.py مش بيخزّنه). للتفريق بين النسخ المتضاربة استخدم `version`، أو نخزّن تاريخ الـfrontmatter في مهمة لاحقة.
- فلتر إضافي `d.status = 'active'` (PRD 10.5: المستندات الـInactive مابتظهرش في الاسترجاع). النسختين الحاليتين active فمش مأثّر على الحالة التالتة.
- role أو category مش معروفين → `ValueError` (مش `PermissionDeniedError`)، عشان category متألفة من الـLLM ماتطلعش للموظف كـ"مش مسموح لك" وهي أصلاً مش موجودة.
- `top_k` محصور في [1, 20].
- الـsession factory بتتجاب **قبل** الـembedding: لو `DATABASE_URL` ناقص، نفشل من غير ما نصرف request من Gemini.
- السكريبت بيعمل `sys.stdout.reconfigure(encoding="utf-8")` — من غيره بيقع بـ`UnicodeEncodeError` على Windows لما الـoutput يتعمله redirect/pipe (نفس المشكلة موجودة في `ingest.py`، ماتعدلش لأنه برا النطاق).
- **Security:** كل قيم الـSQL bind parameters (مفيش f-string SQL)؛ الـcategory اللي هيقترحها الـLLM بتتفحص ضد allowlist. مخاطر مفتوحة: (1) الاتصال بيوزر `postgres` اللي بيتخطى الـRLS، فالفلترة في الكود هي الطبقة الوحيدة حالياً — يُفضل role read-only مخصص للـretrieval لما نضيف الـRLS. (2) `sslmode=require` بيشفّر بس مش بيتحقق من الـcertificate — `verify-full` محتاج Supabase CA cert. (3) لما نبني `/chat`: الـ`role` لازم ييجي من الـJWT/`profiles` بس، أبداً من الـrequest body أو الـLLM.
- **Test Guard:** مفيش mocks، والاختبار على الداتابيز الحقيقية (Rule 9). ثغرة متعلّمة: مفيش حالة لـ`hr` **من غير category** — ده المسار اللي الـagent هيستخدمه لو ماحددش category، ومحتاج اختبار يتأكد إن مفيش chunk من `property_listings`/`payment_policies` بيرجع. كمان السكريبت يدوي؛ Tech-Stack بيحدد pytest تحت `backend/tests/` — يتحوّل لما نعمل الـtest suite.
- **Clean Code:** `ALL_CATEGORIES` متشتقة من الـmapping، بس نفس المعرفة متكررة في `VALID_CATEGORIES` (ingest.py) والـCHECK constraint في schema.sql — يُفضل مصدر واحد مشترك في refactor لاحق.
- **تحديث 2026-11-09 — اتشغّل end-to-end:** بعد إضافة `DATABASE_URL` للـ`.env`، `python -m scripts.test_retrieval` (من `backend/`) اتشغّل على داتابيز Supabase الحقيقية وطلع **4/4 passed** (الـ3 حالات بتوع المهمة دي + الحالة الرابعة من الـentry اللي تحت). أهم حالتين: `sales → payment_policies` رجّع النسختين `2025.1` و`2026.1` (حالة التضارب المقصودة قابلة للاسترجاع، وحلها مسؤولية الـagent layer)، و`hr` من غير category فضل محصور في `company_info_support` بس. الـ⚠️ بتاع `DATABASE_URL` فوق اتحل.

**الحالة:** ✅ تم

---

## 2026-11-08 — Phase 1: اختبار الـdefault scope للصلاحيات (الحالة الرابعة)

**تم:**
- ضفنا `case_hr_no_category_scoped_to_allowed` لـ`test_retrieval.py`: `role="hr"` من غير category، والـassertion إن النتيجة مش فاضية وكل الـchunks من `company_info_support` بس. ده بيقفل الثغرة اللي Test Guard علّم عليها في المهمة اللي فاتت — المسار اللي الـagent هيمشي فيه لو ماحددش category.

**ملفات اتعملت/اتعدلت:**
- backend/scripts/test_retrieval.py — حالة رابعة + `HR_GENERAL_QUERY`، وعدد طلبات Gemini في الـdocstring بقى 3

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- السؤال "العام" اتاختار مايل ناحية الوحدات والأسعار عن قصد (`What units are available, how much do they cost, and how can I contact the company?`). سؤال زي "عن الشركة" كان هيرجّع `company_info_support` حتى لو الفلترة مكسورة، فالاختبار ماكانش هيثبت حاجة.
- اتأكدنا إن الاختبار بيفرّق فعلاً (offline، بحساب الـcosine في Python على الـembeddings الحقيقية): بحث **من غير فلترة** كان هيرجّع 4 من 5 من `property_listings`/`payment_policies` (المراكز 2–5، بـsimilarity 0.628–0.646) → الحالة هتفشل. بالفلترة الحالية (`resolve_categories("hr", None) == ["company_info_support"]`) الـtop 5 كلهم `company_info_support` (0.573–0.648) → الحالة هتعدّي.
- `bool(chunks)` جزء من الـassertion: نتيجة فاضية كانت هتعدّي شرط "مفيش category ممنوعة" من غير ما تثبت إن البحث اشتغل.
- **Test Guard:** مفيش violations — assertion على الـreturn value (Rule 1)، مفيش mocks (Rule 2)، بتمسك bug مافيش حالة تانية بتمسكه (Rule 4)، الاسم بيوصف السيناريو والنتيجة (Rule 5)، داتابيز حقيقية (Rule 9). الحالة 1 والحالة 4 شكلهم متشابه بس سيناريوهات مختلفة (category صريحة مقابل الـdefault scope) — ينفع يتعملهم `parametrize` لما السكريبت يتحوّل لـpytest.
- السكريبت ماتشغّلش end-to-end لسه: `DATABASE_URL` لسه مش في الـ`.env`.
- **تحديث 2026-11-09:** الحالة دي عدّت على الداتابيز الحقيقية ضمن نفس تشغيلة `python -m scripts.test_retrieval` المسجّلة في entry الـPermission-aware retrieval فوق (**4/4 passed**) — الـ4 حالات بيتشغلوا مع بعض في نفس السكريبت، فمكانش محتاج تشغيل منفصل. `hr` من غير category فضل محصور في `company_info_support` بس.

**الحالة:** ✅ تم

---

## 2026-11-09 — Phase 1: هيكل الـFastAPI backend (‏/chat و/conversations و/models)

**تم:**
- `POST /chat`: محادثة جديدة لو مفيش `conversation_id` (الـtitle = أول 50 حرف من السؤال) ← حفظ رسالة الـuser ← `retrieve_chunks(top_k=5)` ← رد OpenRouter بـstreaming (SSE) ← حفظ رد الـassistant بالمصادر بتاعته. `PermissionDeniedError` ← event واحد `denied` من غير LLM. مفيش chunks ← "مش لاقي ده في بيانات الشركة" مباشرة، برضه من غير LLM.
- System prompt للـgrounded RAG: الإجابة من الـcontext بس، الـcitation بعنوان المستند بعد كل معلومة، وبنفس لغة السؤال. الـchunks جوه `<context>` وكل واحد في `<document title version section>`.
- `GET /conversations?user_id=` (الأحدث الأول) و`GET /conversations/{id}?user_id=` (المحادثة + رسايلها بالترتيب الزمني بالمصادر).
- `GET /models`: موديلات OpenRouter المجانية (id, name, context_length). أي فشل من OpenRouter (network، status غلط، JSON بايظ) ← 502 برسالة واضحة.
- `app/main.py`: الـapp + CORS لـ`http://localhost:3000` + الـ3 routers. التشغيل: `uvicorn app.main:app --reload` من `backend/`.
- عمود `messages.sources jsonb` — مكانش موجود في schema.sql، اتضاف بـmigration (شوف الـblockers تحت).
- اختبار يدوي `scripts/test_chat_endpoint.py` (اخترنا Python script مش curl، زي `test_retrieval.py`): 4 حالات — `/models`، و`sales` بيعمل stream والرد بيتحفظ زي ما اتبعت بالظبط، و`hr → property_listings` بيرجّع `denied` بس ومفيش رد assistant بيتحفظ، وحالة زيادة إن موديل مدفوع بيرجّع 422 قبل أي كتابة في الداتابيز.

**فجوات معروفة لازم تتقفل في المراحل الجاية (عليها marker `# TEMPORARY:` في الكود):**
1. **مفيش auth حقيقي** — `# TEMPORARY: replace with JWT-derived role/user_id once auth is built` في 4 أماكن: `ChatRequest.role` و`ChatRequest.user_id` (chat.py)، والـ`user_id` بتاع `GET /conversations` و`GET /conversations/{id}` (conversations.py). أي client يقدر يبعت أي `role` (يعني hr يقول إنه sales ويشوف الأسعار)، وأي `user_id` (يعني يقرا محادثات حد تاني لو عرف الـUUID بتاعه). الـrole كمان مش بيتقارن بـ`profiles.role`. فالـpermission layer شغالة صح بس مدخلها مش موثوق فيه. الـbackend ده **ماينفعش يتعمله deploy** قبل ما ده يتقفل.
2. **مفيش category routing من الـagent** — `# TEMPORARY: naive retrieval, replace with LangGraph agent's category routing in the next phase` في chat.py عند الـcall بتاع `retrieve_chunks`. الـcategory بتيجي من الـclient زي ما هي (أو `None` = كل الـscope المسموح للـrole)، ومفيش حل لتضارب النسخ (2025.1 مقابل 2026.1) غير إن الـversion ظاهر للموديل في الـattributes.

**ملفات اتعملت/اتعدلت:**
- backend/app/core/config.py — pydantic-settings، فيه `OPENROUTER_API_KEY` بس (SecretStr، ممنوع يبقى فاضي)
- backend/app/llm/openrouter_client.py — `list_free_models()` (httpx) و`stream_chat_completion()` (openai SDK، `max_tokens=2048`)
- backend/app/llm/prompts.py — الـgrounded system prompt و`NOT_FOUND_MESSAGE`
- backend/app/db/conversation_store.py — قراية/كتابة conversations وmessages بـSQL بـbind params على session.py
- backend/app/db/migrations/001_add_messages_sources.sql — إضافة `messages.sources jsonb not null default '[]'`
- backend/app/db/schema.sql — عمود `sources` في تعريف جدول messages (عشان أي setup جديد يبقى مطابق)
- backend/app/api/models.py — `GET /models` + `fetch_free_models_or_502` (مستخدمة في /chat كمان)
- backend/app/api/conversations.py — `GET /conversations` و`GET /conversations/{id}`
- backend/app/api/chat.py — `POST /chat` بـSSE
- backend/app/main.py — الـFastAPI app وCORS والـrouters
- backend/app/core/\_\_init\_\_.py، backend/app/llm/\_\_init\_\_.py، backend/app/api/\_\_init\_\_.py — فاضيين
- backend/scripts/test_chat_endpoint.py — الاختبار اليدوي (4 حالات)
- backend/requirements.txt — `openai==3.46.0` و`jiter==0.19.0` (dependency بتاعة openai). النسخ متأكد منها بـ`pip show`. `httpx==0.28.1` و`pydantic-settings==2.16.2` و`fastapi`/`uvicorn` كانوا موجودين أصلاً. الملف فضل UTF-16 LE + CRLF زي ما هو.

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- **config.py فيه `OPENROUTER_API_KEY` بس:** الـkeys التانية بتتقرا فعلاً في مكانها: `DATABASE_URL` في session.py، و`SUPABASE_URL`/`SUPABASE_SERVICE_KEY` في supabase_client.py، و`GEMINI_API_KEY` في embeddings.py. عشان كده مااتكرروش، وmain.py بيعمل `load_dotenv()` عشانهم. تجميعهم كلهم في config.py هيبقى refactor منفصل.
- **Fail fast على الـkey:** main.py بينادي `get_settings()` وقت الـimport، فالـserver مابيقومش لو `OPENROUTER_API_KEY` ناقص أو فاضي. من غير ده /chat كان هيقع جوه الـstream بعد ما الـ200 اتبعتت، والـclient يوصله رد مقطوع. المشكلة دي ظهرت فعلاً في الـsmoke test: الـkey موجود في الـ.env بس قيمته فاضية، وكان بيطلع "Missing credentials" مضللة من الـopenai SDK.
- **بروتوكول الـSSE:** الـdata في كل event عبارة عن JSON في سطر واحد، عشان الـnewlines اللي جوه النص ماتكسرش الـframing. الـevents: `token {text}`، `done {sources}`، `denied {message}`، `error {message}`. الـ`conversation_id` بيرجع في header ‏`X-Conversation-Id` (مفتوح في CORS بـ`expose_headers`).
- **الموديل لازم يكون مجاني:** /chat بيرفض (422) أي model مش في قائمة `/models`، وده قبل أي كتابة في الداتابيز. غير كده أي client يقدر يصرف من رصيد الـAPI key على موديل مدفوع. التمن: كل /chat بيعمل request لـOpenRouter /models (مفيش cache لسه). الـfilter بيستبعد الـrouters اللي سعرها `-1` وأي موديل عنده `pricing.overrides` (أسعار tiered). النتيجة دلوقتي 16 موديل، منهم `openrouter/free`، ومنهم كمان موديلات مش نصية (Lyria بتاع audio) — الـUI محتاج يفلترها أو نضيف filter بالـmodality.
- **`user_id` مطلوب في `GET /conversations/{id}` كمان** (مش مذكور في الـspec): الـquery بتفلتر بـ`id AND user_id`، و404 سواء المحادثة مش موجودة أو بتاعة حد تاني. نفس الـcheck في /chat لما يتبعت `conversation_id`. و`user_id` مش موجود في profiles ← 404 (من الـIntegrityError بتاع الـforeign key).
- **الـrole والـcategory المش معروفين ← 422** من الـvalidation قبل أي كتابة. أما "معروفة بس مش مسموحة" فبتوصل لـ`retrieve_chunks` وبترجّع `denied`. الرسالة محدودة بـ`MESSAGE_MAX_CHARS = 4000`.
- **الـdenial مش بيتحفظ كـرد assistant:** الـspec بيقول "stream a single event and return". فالـhistory هيظهر فيه رسالة الـuser من غير رد — الـfrontend محتاج يعرض ده صح. أما رد "مش لاقي ده" (لما مفيش chunks) **بيتحفظ** بـ`sources=[]`، لأنه رد حقيقي بعد بحث حصل فعلاً.
- **مفيش similarity threshold:** `retrieve_chunks` بيرجّع دايماً top 5 لو فيه مستندات active، فالقائمة الفاضية نادرة. الأسئلة اللي ملهاش إجابة فعلاً بتعتمد على قاعدة 4 في الـprompt (الموديل يقول الجملة دي بالنص). الـthreshold محتاج يتحدد بـevaluation في Phase 4، مش برقم نختاره بالتخمين.
- **الـsources المتخزنة = الـchunks الـ 5 اللي اتبعتت للموديل** (`chunk_id, doc_id, doc_title, version, section, similarity_score`)، مش بس اللي اتذكرت في الـcitations. استخراج الـcitations من النص مش موثوق فيه.
- **مفيش conversation history بيتبعت للموديل:** كل سؤال بيتبعت لوحده (system + user). الـmemory جزء من الـagent phase.
- **فشل OpenRouter في النص (`openai.APIError`) أو رد فاضي** ← event اسمه `error`، والرد مش بيتحفظ. التفاصيل بتتسجل في الـlog بس ومش بتوصل للـclient. لو الـclient قفل الاتصال في النص، الـstream لـOpenRouter بيتقفل (`async with`) وبرضه مفيش حاجة بتتحفظ. اتجرّب live بـkey غلط: 401 ← `error` event ومفيش محاولة حفظ.
- `max_tokens=2048` على الـcompletion (LLM10 — Unbounded Consumption). الرقم عالي بما يكفي لأن الـreasoning tokens بتتحسب من نفس الحد.
- الـendpoint بتاع /chat معمول `def` عادية (الـDB والـretrieval sync فبيشتغلوا في الـthreadpool). الـfree-model check معمول async dependency. والحفظ جوه الـasync generator بيستخدم `run_in_threadpool` عشان مايعملش block للـevent loop.
- `openai==3.46.0` (major 3): الـAPI اللي اتستخدم (`AsyncOpenAI`، `chat.completions.create(stream=True)`، `delta.content`، `APIError`) اتأكدنا منه من الـpackage المتسطب. openai عنده `PermissionDeniedError` بنفس اسم اللي في retrieval، فchat.py بيعمل import لـ`APIError` بس من openai.
- **Code Security + llm-security:**
  - اللي اتعمل: كل الـSQL بـbind params (مفيش f-string SQL)، الـkey متخزن SecretStr ومش بيظهر في logs، الـerrors مش بتكشف تفاصيل داخلية للـclient، CORS محصور في origin واحد من غير credentials، الـURL بتاع OpenRouter ثابت (مفيش SSRF)، والـmodel id بيتفحص ضد allowlist.
  - Prompt injection: الـchunks جوه delimiters، وقاعدة 5 بتقول إنها بيانات مش تعليمات، وسؤال الموظف في رسالة user منفصلة. ما فيش أسرار في الـsystem prompt. الموديل ملوش tools أصلاً، فأقصى ضرر لـinjection هو نص غلط — مش تسريب بيانات لأن الـcontext متفلتر بالـrole قبل ما يوصل للموديل.
  - مخاطر مفتوحة: (1) الـrole/user_id المش موثقين (TEMPORARY رقم 1 فوق) — ده الأخطر. (2) الاتصال بـ`postgres` اللي بيتخطى الـRLS، فالـownership check اللي في الكود هو الطبقة الوحيدة. (3) مفيش rate limiting: أي client يقدر يخلّص الـfree quota بتاعة OpenRouter (50 request في اليوم) أو يملا الداتابيز بمحادثات. مالوش معنى قبل الـauth لأن الـrate limit لازم يبقى per-user موثق. (4) رد الموديل untrusted (LLM05): الـfrontend لازم يعرضه كـtext أو markdown متعمله sanitize، أبداً `dangerouslySetInnerHTML`. (5) الـattributes بتاعة `<document>` (title/version/section) مش متعمللها escape. دي بيانات الـAdmin بس دلوقتي، بس تتراجع لما الـupload يتفتح في Phase 3. (6) `GET /conversations` مفيهاش pagination.
- **Clean Code Guard:** مفيش imports مش مستخدمة (اتأكدنا بـAST pass، لأن مفيش linter متسطب). اللي اتصلح أثناء الـpass: الـkey الفاضي بقى مرفوض، الـfail fast، رد 200 بـJSON بايظ من `/models` بقى 502 بدل 500 (اتجرّب: JSON بايظ، `data` ناقصة، و503)، و`post_chat` في الاختبار كان بياخد 5 parameters ونزل لـbody واحد. المتعلّم عليه للمراجعة: `_stream_grounded_answer` طولها ~27 سطر (flow واحد في خط مستقيم، سيبناها). ومعرفة الـcategories لسه متكررة في retrieval.py وingest.py وschema.sql (من الـentry اللي فاتت).
- **Test Guard:** مفيش violations. الاختبار شغال على الـHTTP بس من غير mocks، وعلى داتابيز وOpenRouter حقيقيين. كل حالة بتمسك bug مختلف. ومفيش assertion على صياغة رد الموديل أو الـcitations (Rule 10، لأنها مش deterministic) — جودة الإجابة دي شغلانة RAGAS في Phase 4. المحادثات اللي الاختبار بيعملها بتتمسح في `finally`. ولو فيه متطلبات ناقصة بيطلع exit 2 مع قايمة بالناقص.
- **اللي اتجرّب فعلاً:** `GET /models` رجّع 200 وفيه 16 موديل، والـ502 اتجرّبت بـtransport متبدّل. الـvalidation بترجّع 422 (role/category مش معروفين، رسالة فاضية، UUID غلط، موديل مدفوع). 404 لموظف مش موجود ولمحادثة مش بتاعته. الـCORS اتجرّب (localhost:3000 مسموح، وorigin تاني مرفوض). مسار الـretrieval للـprompt للـstream اتجرّب live لحد OpenRouter (401 لأن الـkey فاضي). وحالتين من الـtest script (`/models` والموديل المدفوع) عدّوا.

**Blockers قبل ما `/chat` يتجرّب end-to-end** (`python -m scripts.test_chat_endpoint` بيطلع exit 2 وبيقول الـ 3):
1. `OPENROUTER_API_KEY` موجود في `backend/.env` بس قيمته فاضية — والـserver مش هيقوم من غيره.
2. `migrations/001_add_messages_sources.sql` لسه ماتطبّقتش — لازم تتنفذ مرة واحدة في Supabase SQL Editor. من غيرها أي كتابة أو قراية للرسايل هتقع.
3. `profiles` و`auth.users` **فاضيين** في الداتابيز الحقيقية، مع إن `docs/demo-accounts.md` بيوصف 3 حسابات. من غير profiles مفيش محادثة تتعمل (foreign key). ماعملناش seed لأنها بيانات auth برا نطاق المهمة.

**الحالة:** ⚠️ تم جزئياً — الكود كله اتكتب واتجرّب في كل حتة ينفع تتجرّب دلوقتي. مسار الـstreaming + الحفظ + الـdenial بتاع `/chat` ماتجرّبش end-to-end لسه بسبب الـ 3 blockers اللي فوق. والـTEMPORARY markers الاتنين فجوات مقصودة للمراحل الجاية.

---

## 2026-11-09 — Phase 1: متابعات على هيكل الـbackend (idempotency في /chat + cache + text filter + موديل محدد للاختبار)

> متابعة مباشرة لـentry "Phase 1: هيكل الـFastAPI backend" — 5 إصلاحات معتمدة بالظبط، والنطاق محصور في `chat.py` و`openrouter_client.py` و`test_chat_endpoint.py`.

**تم:**
1. **تأجيل الكتابة لحد بعد الـretrieval** (`chat.py`): الـconversation-create وinsert رسالة الـuser بقوا بعد ما `retrieve_chunks()` ينجح. لو الـretrieval فشل أو رجّع `PermissionDeniedError`، مفيش أي صف بيتكتب في `conversations` أو `messages` — الـclient بيستلم الـdenied/error من غير orphan rows. قبل كده، الـdenial كان بيسيب محادثة جديدة برسالة user من غير رد.
2. **الـretrieval failure بقى SSE `error` مش 500 خام** (`chat.py`): الـcall بتاع `retrieve_chunks` متغلف بـtry/except — `PermissionDeniedError` الأول (denied)، وأي exception تاني (داتابيز، Gemini embedding، أي حاجة) بيتسجل بـ`logger.exception` على الـserver وبيطلع `event: error` بنفس شكل الـevent بتاع OpenRouter، من غير ما يكشف تفاصيل داخلية للـclient. الـmessage بتاعه في constant ‏`RETRIEVAL_ERROR_MESSAGE`.
3. **Cache بـTTL 5 دقايق لـ`list_free_models()`** (`openrouter_client.py`): النتيجة بتتخزن in-memory (`time.monotonic` — مش wall clock عشان تغيّرات ساعة النظام مأثراش) وبتترجع copy سطحية. `/chat` (عن طريق `require_free_model` → `fetch_free_models_or_502`) بقى مبيرفعش request لـOpenRouter على كل رسالة.
4. **فلترة الموديلات غير النصية** (`openrouter_client.py`): `_is_text_chat()` بتفحص `architecture` من رد `/models` — الـoutput لازم يكون نصي بالكامل (`output_modalities == ["text"]`) والـinput لازم يقبل `text`. ده استبعد موديلات الـaudio (Lyria الاتنين). موديلات الـvision (input فيه image + output نص) بتفضل عادي لأننا بنبعت text بس.
5. **موديل محدد ومسمّى في الاختبار** (`test_chat_endpoint.py`): `openrouter/free` (الـauto-router اللي بيختار موديل عشوائي وممكن يرجّع رد فاضي أو rate limit) اتبدّل بـ`nvidia/nemotron-3.5-lightning:free` — متجرّب live إنه بيرجّع محتوى غير فاضي بـstreaming.

**قرار الـcache bypass (كان مطلوب اتخذه):** الـcache بيشمل `GET /models` نفسه مش `/chat` بس، ومفيش bypass متطبق فعلاً دلوقتي. السبب: `models.py` برا نطاق المهمة، والاتنين (`GET /models` و`require_free_model`) بيعدّوا على نفس `list_free_models()` — لو الـendpoint فضل fresh والـchat check فضل stale، الـdropdown ممكن يورّي موديل الـ`/chat` يرفضه لحد 5 دقايق. cache واحد للاتنين = اتساق. `force_refresh: bool = False` متوفرة كـparameter لما يتريد تحديث القائمة قسرياً (مثلاً لما `models.py` يتبنى عليها في مهمة لاحقة).

**تغيير سلوك مرئي للـfrontend:** الـdenied لمحادثة **جديدة** مبيرجعش `X-Conversation-Id` خالص (مفيش حاجة اتعملت في الداتابيز أصلاً)، والـdenied لمحادثة موجودة مبيرجعش الـid بتاعها. الـclient محتاج يتعامل مع الـdenied/error كـ"مفيش حاجة اتحفظت" — مش "اتحفظت نص". للمحادثة الموجودة، فحص الملكية (404) لسه بيحصل قبل الـretrieval كقراية بس، عشان الـ404 يرجع قبل ما نصرف embedding.

**ملفات اتعملت/اتعدلت:**
- backend/app/api/chat.py — تأجيل الكتابة بعد الـretrieval، try/except حوالين `retrieve_chunks` بـerror event مسجّل، `_resolve_conversation` اتقسمت لفحص ملكية (قراية، بدري) + `_create_conversation` (كتابة، متأخرة)، `_sse_response` بقت تقبل `UUID | None` وتبعت الـheader بس لو فيه conversation
- backend/app/llm/openrouter_client.py — cache بـTTL 5 دقايق + `force_refresh`، فلتر `_is_text_chat()` على `architecture`
- backend/scripts/test_chat_endpoint.py — `CHAT_MODEL` بقى موديل مسمّى، حالة الـdenial بقت بتتأكد إن مفيش كتابة خالص (قبل/بعد في عدد المحادثات + عدم وجود الـheader)، والـdocstring اتحيّن (عدد الـrequests المستهلكة)

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- **اتجرّب فعلاً (من غير profiles):** الجلب fresh ‏1.36s مقابل cached ‏0.0000s بنفس القائمة (الـcache شغال)، القائمة 16 → 14 موديل بعد فلتر النص (Lyria اختفت)، `GET /models` رجّع 200، الموديل المدفوع 422، الـdenial طلع event واحد `denied` من غير header ومن غير أي كتابة، والـretrieval failure طلع `event: error` ‏200 مع traceback كامل في اللوج (اتجرّب بـ`DATABASE_URL` مكسورة عمداً في subprocess منفصل). كمان اتأكدنا إن `user_id` مش موجود بيرجّع 404 بعد نجاح الـretrieval ومن غير أي صف يتكتب.
- **Blockers القديمة:** رقم 1 (الـkeys) ورقم 2 (migration 001) اتحلّوا من الدورة اللي فاتت — اتأكدنا إن عمود `sources` موجود فعلاً. رقم 3 (`profiles`/`auth.users` فاضيين) لسه قايم؛ اتعرض عمل seed للـdemo accounts بالـAdmin API واترفض، فالـstreaming + الحفظ مازالوا ماتجرّبوش end-to-end.
- **ملاحظة مكتشفة أثناء الاختبار (برا النطاق):** `retrieve_chunks` بيحسب الـembedding **قبل** ما يجرب يفتح اتصال الداتابيز — يعني فشل الداتابيز بيصرف request من Gemini على الفاضي. المصدر retrieval.py (برا النطاق هنا)؛ يتحط في اعتبار مهمة الـretrieval الجاية.
- **Clean Code Guard:** مفيش imports مش مستخدمة (AST pass زي المرة اللي فاتت). اللي اتصلح أثناء الـpass: أول صياغة لحالة الـdenial في الاختبار كانت بتقرا أول محادثة عند الـhr — كانت هتفشل لو ليه محادثات قديمة، فبقت قبل/بعد زي حالة الموديل المدفوع. المتعلّم عليه: `force_refresh` ‏boolean flag من غير caller في الـrepo لحد ما `models.py` يتبنى عليه (مطلوب صراحة في المهمة)، و`chat()` بقت ~28 سطر (flow خطي، زي ما اتقرر على `_stream_grounded_answer` قبل كده).
- **Code Security:** مفيش SQL جديد (كل الكتابة لسه بـbind params في conversation_store)؛ رسالة الـerror مش بتكشف تفاصيل داخلية؛ الـexception بيتسجل في اللوج بس من غير message الموظف؛ الـcache في الـmemory للعملية بس ومفيهاش أسرار؛ `time.monotonic` محصّنة ضد تغيّرات ساعة النظام. المخاطر المفتوحة من المهمة اللي فاتت زي ما هي (الـrole/user_id مش موثقين، مفيش rate limiting) — دي متأثرة بالتغييرات دي ولا التغييرات أثّرت عليها.
- **Test Guard:** الاختبارات لسه من غير mocks على داتابيز وOpenRouter حقيقيين، وكل حالة بتمسك bug مختلف. حالة الـdenial بقت أقوى (بتثبت عدم الكتابة بدل ما بتثبت حفظ رسالة user من غير رد). الاختبار نفسه مازال manual script — تحويله pytest لما الـtest suite تتبني.
- **ملاحظة على موديل الاختبار:** الموديلات المجانية بتتغير من غير إنذار (PRD قسم 12) — لو `nvidia/nemotron-3.5-lightning:free` اختفى من الطبقة المجانية، الحالة الأولى في السكريبت هتفشل برسالة واضحة، والتبديل سطر واحد في `CHAT_MODEL`.

**الحالة:** ✅ تم — الـ5 إصلاحات اتنفذوا واتجرّبوا بكل الطرق المتاحة من غير seed. مسار الـstreaming + الحفظ لسه محتاج الـdemo accounts (blocker 3) قبل اختبار end-to-end كامل.

---

## 2026-11-09 — Phase 1: سكريبت seed للـdemo accounts (قفل blocker 3)

> متابعة لـentry "هيكل الـFastAPI backend" — الـblocker رقم 3 (`profiles`/`auth.users` فاضيين مع إن `demo-accounts.md` بيوصف 3 حسابات). المهمة دي بتحوّل الـseed من "خطوة يدوية في Dashboard" لسكريبت idempotent في الـrepo.

**تم:**
- سكريبت `backend/scripts/seed_demo_accounts.py` بيعمل الحسابات الثلاثة الموثقة في `docs/demo-accounts.md` (admin/sales/hr — `@reelestate.demo`، كلهم `Demo@2026!`):
  1. مستخدم Auth عن طريق `supabase.auth.admin.create_user()` بـ**service_role** key (من `get_supabase()`) — بـ`email_confirm=True` عشان من غير تحقق إيميل.
  2. صف مطابق في `profiles` (id بتاع المستخدم + role + full_name مشتق من الـrole زي "Sales Demo User").
- **Idempotency:** قبل أي إنشاء، بيدوّر على المستخدم بالإيميل في `auth.users` (عن طريق `list_users` بصفحات 50). موجود → بيتخطى من غير خطأ ولا تكرار، وبس بيتأكد إن صف الـprofiles موجود. لو الـcreate فشل (سباق مع تشغيل تاني)، بيرجّع يدوّر عليه: لقيناه → يتحسب existed، ملقيناهوش → الـexception بيرجّع زي ما هو. صف profiles موجود بيسيب زي ما هو (مفيش تعديل).
- **ملخص في الآخر:** كل حساب وحالته (`created` / `existed (profiles ensured)` / `FAILED: ...`)، والـexit code ‏1 لو أي حساب فشل مع دعوة لإعادة التشغيل (السكريبت idempotent فمفيش ضرر من إعادة المحاولة). الفشل في حساب مابيوقفش الباقي.
- مفيش dependency جديدة — `supabase==2.34.0` كان متسطب ومتسجل في `requirements.txt` أصلاً.

**ملفات اتعملت/اتعدلت:**
- backend/scripts/seed_demo_accounts.py — سكريبت جديد (ملف المهمة الوحيد في الكود)

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- **الباسورد hardcoded في السكريبت مش في `.env`:** عمداً — `demo-accounts.md` مش secret (Tech-Stack قسم 11 بيقول ده صراحة)، وحطه في `.env` هيخلي السكريبت يتطلب إعداد زيادة من غير فايدة أمنية (بيانات وهمية بالكامل). الثوابت في السكريبت بتشاور على الـdoc كمصدر للحقيقة — لو الحسابات اتغيرت هناك لازم تتغير هنا.
- **صف الـprofiles بيعمل select-then-insert** (زي pattern الـupsert في ingest.py) — مش atomic، فسباق حقيقي بين تشغيلين متوازيين ممكن يضرب unique violation على المفتاح. مقبول لسكريبت يدوي؛ وبالمقابل الـauth user نفسه محمي من التكرار (إيميل unique في Supabase).
- **الدوّر بالإيميل مش get-by-email:** الـadmin API مفيهوش `get_user_by_email` — فيه `list_users` بصفحات و`get_user_by_id` بس. بثلاثة حسابات (والمتوقع عدد قليل من الموظفين)، اللف على الصفحات رخيص.
- **Code Security:** الـservice_role key بيقرا من الـenv عن طريق `get_supabase()` الحالية ومش بيظهر في أي output (رسايل الفشل من الـAPI مش بتشمل headers). مفيش SQL خام — كل الكتابة عن طريق الـSupabase client (parameterized جوّه postgrest). `email_confirm=True` هو ده الغرض أصلاً (حسابات demo من غير إيميلات حقيقية — الدومين وهمي)، والسكريبت manual-only مش endpoint.
- **Clean Code Guard:** كل الدوال ≤ 15 سطر، مفيش boolean flags، و`except Exception` الوحيد في `main()` مقصود وموثّق (يكمل الحسابات الباقية ويرجّع فشل في الآخر). مفيش imports مش مستخدمة (AST pass). السكريبت مافيهوش أي تنفيذ عند الـimport — كل الشغل جوه `main()` (اتأكدنا بـimport فعلي).
- **ماتجرّبش run فعلي:** المفروض المستخدم هو اللي يشغّله (ده اللي المهمة طلبته). اللي اتعمل: compile + import نظيف + مراجعة الـAPI المستخدمة من الـpackage المتسطب نفسه (`create_user(AdminUserAttributes)` بـ`email_confirm`، و`list_users(page, per_page)` — الاتنين متأكدين منهم من الكود المتبّت). التشغيل الفعلي هيأكد الباقي، ولو فشل في أي حساب هيقول أيه واللي بعده بيكمل.
- **بعد التشغيل الناجح:** blocker 3 هيتقفل، وساعتها `python -m scripts.test_chat_endpoint` (بعد `OPENROUTER_API_KEY` وmigration 001 اللي اتحلوا) يبقى قادر يعدي مسار الـstreaming + الحفظ end-to-end لأول مرة.

**الحالة:** ⚠️ تم جزئياً — السكريبت كتب واتراجع (Code Security + Clean Code Guard) بس محتاج تشغيل فعلي للتأكيد: `python -m scripts.seed_demo_accounts` (من `backend/` والـvenv مفعّلة).

---

## 2026-11-10 — Phase 1: similarity threshold على الـtop-1 (0.60) + أول تشغيل end-to-end كامل للاختبار

> متابعة لـentry "متابعات على هيكل الـbackend". القرار مبني على قياس فعلي بسكريبت `scripts/measure_similarity.py` (throwaway diagnostic — 11 سؤال على الداتابيز الحقيقية، مكتوب في مهمة استكشافية منفصلة من غير ما يتسجل فيها). بعد التشغيل، اتأكدنا إن الحسابات الـdemo اتبント (توسيط المهمة اللي فاتت) — فالاختبار الـend-to-end بقى ممكن لأول مرة.

**القرار:** حد صلة ‏`RETRIEVAL_RELEVANCE_THRESHOLD = 0.60` بيتطبق على **الـtop-1 بس** (أعلى chunk في النتيجة، مش كل الـchunks الـ5). لو أعلى نتيجة أقل من 0.60، بيتعامل مع الطلب كأن الـretrieval رجّع فاضي: الرد الجاهز "مش لاقي ده في بيانات الشركة" بيتبعت مباشرة من غير LLM، وبيتحفظ بـ`sources=[]` — نفس سلوك حالة القائمة الفاضية بالظبط.

**الـrationale (من القياس الفعلي):**
- الأسئلة اللي ليها إجابة فعلية (on-topic، 4 أسئلة): أعلى نتيجة لكل سؤال بين **0.7074 و0.7870**.
- الأسئلة اللي ملهاش أي علاقة (off-topic، 4 أسئلة): أعلى نتيجة بين **0.4713 و0.5113**.
- الأسئلة الحدودية (borderline، 3 أسئلة): الإيجار **0.5557** والتمويل **0.5651** — مواضيع مش موجودة في البيانات أصلاً، والاتنين تحت 0.60 صح. العقارات التجارية **0.6275** — **هتعدي الـthreshold غلط، وده استثناء معلوم ومقبول**: ماينفعش نرفع الـthreshold لـ0.63 عشانه لأننا هنبطل أسئلة on-topic حقيقية (الحد الأدنى 0.707 قريب من حواف الـnoise). بيتقفل بـself-check بتاع الـagent في مرحلة LangGraph (Phase 2)، مش بالـthreshold.
- **ليه top-1 بس:** في الأسئلة اللي ليها إجابة، الـranks 2–5 بينزلوا تحت 0.60 عادي (مثال: سؤال مارينا هايتس ‏0.787 → 0.624). threshold على كل الـchunks هيقطع context مفيد من نفس السؤال الصحيح.

**تم:**
- `RETRIEVAL_RELEVANCE_THRESHOLD = 0.60` كـconstant فوق `chat.py` بتعليق بيشرح أصل الرقم من القياس (مش تخمين) وبيشاور على `measure_similarity.py`، مع الاستثناء المعلوم (الأسئلة التجارية).
- شرط الحالة الفاضية بقى: `not chunks or chunks[0].similarity_score < RETRIEVAL_RELEVANCE_THRESHOLD` — نفس الرد ونفس الحفظ في الحالتين (الموديل مابيشوفش أي context في الحالتين).

**ملفات اتعملت/اتعدلت:**
- backend/app/api/chat.py — الـconstant + شرط الـtop-1 المدمج مع حالة القائمة الفاضية

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- **أول تشغيل end-to-end كامل ناجح للاختبار اليدوي:** `python -m scripts.test_chat_endpoint` طلع **4/4 passed** (الـ3 blockers القدام اتقفلوا كلهم). أهم حاجة اتأكدت: مسار الـstreaming + الحفظ بقى شغال فعلاً — سؤال التقسيط رجّع 29 token والرد والمصادر اتحفظوا زي ما اتبعتوا بالظبط، والمصادر ضمت النسختين المتضاربتين (2025.1 و2026.1) زي ما متوقع.
- **مسار تحت الـthreshold اتجرّب live:** سؤال الطقس (أعلى نتيجة قياسه ≈ 0.50) رجّع `token` واحد بالرد الجاهز + `done` ‏`sources=[]`، واتحفظ في الداتابيز (user + assistant بمصادر فاضية)، والموديل مااتطلبش منه حاجة — يعني الحاجة الوحيدة المستهلكة هي request الـembedding.
- **سلوك الحفظ لسه زي ما كان:** الرد الجاهز بيتحفظ كرد assistant حقيقي (بعد بحث حصل فعلاً) بـ`sources=[]` — زي حالة القائمة الفاضية قبل كده بالظبط.
- **Code Security:** الـthreshold server-side constant مش من الـclient — لو كان من الـrequest كان بيبقى vector للتلاعب (موظف يبعت threshold=0 يستقبل أي حاجة). التغيير بيقلل سطح الـprompt injection: محتوى غير ذي صلة مبقوش يوصل للموديل أصلاً. مفيش أي SQL جديد أو سطح إدخال جديد.
- **Clean Code Guard:** الحالتين (فاضي / تحت الحد) في branch واحد لأنهم قاعدة واحدة — "مفيش context يقدر يجاوب"، مش تكرار نص. `chunks[0]` أعلى نتيجة بثقة في contract الـretrieval (`ORDER BY distance` موثق في retrieval.py). مفيش أي حاجة تتصلح — الـpass نضيف.
- **ملاحظة تشغيلية:** الـthreshold مبني على 11 سؤال بس من توزيع حقيقي؛ هيتراجع في Phase 4 بـgolden dataset الـRAGAS (30-50 سؤال) — لو الحدود اتزحلقت، الرقم بيتعدل في مكان واحد.
- **سكريبت القياس ماقسّش حاجة في الاختبار اليدوي:** سؤال التقسيط في الاختبار أعلى نتيجته 0.778 > 0.60 فمعدّي عادي؛ لو المحتوى اتغير وسال الاختبار نزل تحت الـthreshold، الحالة التانية هتفشل برسالة واضحة — دي النقطة اللي هتنبه إن الـthreshold محتاج مراجعة.
- **الاختبارات اتشغلت بعد التغيير:** 4/4 + الـprobe بتاع تحت الـthreshold. الـexit codes والحذف في `finally` شغالين زي ما هما.

**الحالة:** ✅ تم — الـthreshold متطبق واتجرّب في الاتجاهين (فوق/تحت)، والاختبار اليدوي عدّى end-to-end كامل (4/4) لأول مرة. الاستثناء المعلوم (الأسئلة التجارية 0.6275) متسجل كمهمة لـPhase 2 (self-check بتاع الـagent).

---

## 2026-11-11 — Phase 2a: الـagent بـLangGraph (توجيه الـcategory + فحص الصلاحية + memory)

**تم:**
- **Graph من 5 nodes** في `app/agent/`: `load_history → decide_category → check_permission → retrieve → respond` مع مخرجين شرطيين (denied بعد `check_permission`، not-found بعد `retrieve`) — الفلو الموثّق في PRD قسم 6 بالظبط. `respond` جوه الـgraph بيكتب tokens على الـstream writer بتاع LangGraph (`{"type": "token"|"error", ...}`) و`/chat` بيحوّلها لـSSE حرفياً — بروتوكول الـevents (token/done/denied/error) زي ما هو بالظبط.
- **`check_permission` كود ثابت (deterministic) مش LLM**: بتقرا من الـstate **بس** `role` و`decided_category` (مفيش سؤال ولا history ولا أي نص مولّد)، ومتكلفة عن `resolve_categories()` في retrieval.py من غير تكرار. الفرق الحرج متطبق ومُختبَر أوفلاين: category معروفة مش مسموحة = رفض حقيقي برسالة PRD نقطة 5؛ category **مختلقة** = مش رفض — fallback لـNone (scope الـrole كامل) والسؤال بيكمّل عادي.
- **`decide_category` بـprompt-then-parse + allowlist صارم**: برومبت بيوصف الـ3 categories ويردّ token واحد، والـparse بيقبّل الرد ضد أسماء الـ3 بس. أي parse فاشل أو output مش معروف أو فشل نداء (`APIError`) = `decided_category=None` — ممنوع نمنع الموظف لأن نداء التوجيه باظ (قرار معتمد؛ الفشل الآمن دايماً = بحث في scope الـrole).
- **`retrieve` بنفس `retrieve_chunks()` من غير تعديل** — والـre-check الداخلي بتاعها فضل طبقة حماية تانية (defense in depth). حد الصلة 0.60 (top-1) اتنقل من chat.py **حرفياً** للـnode بنفس الـcomment والقياس.
- **Memory**: `load_history` بتقرا آخر 10 رسايل من جدول `messages` عن طريق `conversation_store.list_messages()` — من غير checkpointer، الجدول هو مصدر الحقيقة. الـhistory بتغذّي برومبت التوجيه (لحل references زي "والتاني؟") وبرومبت الإجابة. اتراجعت مباشرة على الداتابيز الحقيقية: 12 رسالة → آخر 10 بالترتيب، ومحادثة مش موجودة → فاضية من غير ما نقع.
- **`/chat` بقى بيشتغل بالـgraph**: الـendpoint بقى `async`، بيسحب الـstream لحد ما "مصير الطلب يتحسم" (denied/مش لاقي/فيه إجابة)، وساعتها بس بيحفظ، وبعدين بيكمل الـstream للـSSE. كده `X-Conversation-Id` بيرجع صح حتى للمحادثة الجديدة (بتتعمل قبل ما الـresponse يبعت). **الـ`category` اتحذفت من الـrequest خالص** — الحقل والـvalidator وأي client ملوش كلمة في التوجيه.
- `complete_chat()` — نداء non-streaming صغير في openrouter_client.py لنداء التوجيه.

**⚠️ قرار معتمد مُنفَّذ — تغيير invariant حفظ الرفض (مش مدفون في الكلام):**
- **الرفض دلوقتي بيتحفظ في الداتابيز**: رسالة الـuser + رد assistant بنص رسالة الرفض اللي ظهرت للموظف **بالظبط** (من غير الـcategory المقترحة ولا الـrole ولا أي تفاصيل داخلية)، بـ`sources=[]`. المحادثة الجديدة على الرفض بترجّع `X-Conversation-Id` (قبل كده الرفض مكانش بيكتب أي حاجة ومفيش header) — **السلوك اتغيّر عمداً** حسب القرار المعتمد، والاختبار اتحدّث (بدل "مفيش كتابة" بقى assertion على الحفظ بالنص الحرفي).
- invariant "مفيش orphan rows" لسه شغال: المحادثة ورسالة الـuser بيتكتبوا **بعد ما مصير الطلب يتحسم جوه الـgraph** (رفض / مش لاقي / فيه إجابة) — أي استثناء غير متوقع (داتابيز/embedding) مافيش أي كتابة، زي ما كان.

**ملفات اتعملت/اتعدلت:**
- backend/app/agent/\_\_init\_\_.py — فاضي (package marker)
- backend/app/agent/state.py — `AgentState` TypedDict (total=False) بالحقول المعتمدة: user_id, role, question, conversation_id, model, history, decided_category, permission_result, denial_message, retrieved_chunks, retrieval_ok
- backend/app/agent/nodes.py — الـ5 nodes + `parse_decided_category` + حافتي التوجيه + ثوابت الـthreshold وTOP_K ورسايل error الموديل (اللي كانت في chat.py، منقولين حرفياً)
- backend/app/agent/prompts.py — برومبت تحديد الـcategory بس (برومبت الإجابة فضل في llm/prompts.py زي ما هو، ماتلمسش)
- backend/app/agent/graph.py — `build_graph()` + `get_compiled_graph()` (lru_cache، مرة واحدة لكل عملية)
- backend/app/api/chat.py — إعادة كتابة: حذف `category` + الـvalidator + كومنتات TEMPORARY بتاعتها؛ الـgraph بديل نداء `retrieve_chunks` المباشر؛ كل الكتابة (محادثة/رسايل/رفض) في chat.py بعد حسم المصير؛ `_stream_grounded_answer` اتنقلت منطقياً لـnode الـrespond
- backend/app/llm/openrouter_client.py — `complete_chat()` non-streaming + محاولة واحدة إضافية على الرد الفاضي (شوف الانحرافات)
- backend/scripts/test_chat_endpoint.py — حذف `category` من الـpayloads، حالة الرفض اتجدّدت للحفظ الجديد، `with TestClient(...)` واحد لكل التشغيلة (شوف الانحرافات)
- backend/scripts/test_agent_routing.py — سكريبت جديد بـ9 حالات (فوق) بيطبع تكلفة كل حالة وبيقعد مفهوم لو الـquota خلص في النص

**قرارات تنفيذية اتاخدت (انحرافات معلنة عن الـprompt):**
1. **الكتابة كلها في chat.py مش في الـnodes** (قرار هيكلي): المحادثة الجديدة بتتعمل **بعد** ما الـgraph يحسم المصير — يعني بعد ما الـgraph ابدأ تشغيله، والـid الجديد مش موجود في الـstate بتاع الـgraph الأصلاً. فبدل ما node الـrespond يكتب رد الـassistant بمحادثة مالهاش id، كل الكتابة بقت في طبقة الـAPI بنفس نقاط الضبط المطلوبة (point 6): بعد حسم المصير، قبل الـstreaming، والرفض/الرد الجاهز بيتحفظوا قبل ما الـresponse يبعت. النتيجة: الـnodes مالهاش أي كتابة DB (أسهل اختبار)، والـinvariants متحفظة بالظبط.
2. **`_DECISION_MAX_TOKENS` بقى 2048 + retry واحد على الرد الفاضي** في `complete_chat()`: nemotron بيرجع ساعات content فاضي (reasoning كامل + finish_reason=stop) في النداء الـnon-streaming، واتقاست فعلياً — بـ512 الـreasoning بياكل الميزانية والـcontent مش بييجي خالص، فقرار التوجيه كان بيقع fallback لـNone بالغلط. المحاولة الإضافية الواحدة (مش loop مفتوح) بتقلل التذبذب، وبعد كده الـfallback الآمن شغال.
3. **`with TestClient(app) as client`** في السكريبتين: من غير `with` كل request بياخد event loop جديد، والـAsyncOpenAI client الـcached بيعيد استخدام connections من الـloop المقفول → `RuntimeError: Event loop is closed` في تاني نداء LLM. المشكلة test-harness بس (uvicorn loop واحد في الإنتاج) — ظهرت أول مرة لأن التوجيه دلوقتي بيعمل نداء LLM في **كل** /chat.
4. **assertion الـmemory اترخّات للـflow contract**: الدور التاني لازم يجاوب من غير error بمصادر مش فاضية من الـcategories المسموحة، والدورين في نفس المحادثة (4 رسايل). **دقة توجيه سؤال الضمير نفسها** (هل sources كلها listings؟) دي جودة موديل — بيتقاس في golden dataset بتاع RAGAS (Phase 4) مش في اختبار endpoint، زي قاعدة "مافيش assertion على صياغة/جودة رد الموديل" الموثّقة من Phase 1.
5. الـendpoint بقى `async def` (كان `def`): لازم عشان استهلاك الـstream المزدوج (حسم المصير → رجّع response → كمّل الـstream)، وده اللي بيخلي الـheader صح للمحادثة الجديدة.

**Guard passes:**
- **Code Security:** مفيش SQL جديد ولا سطح إدخال جديد (الـcategory انحذفت من الـrequest — السطح نقص مش زاد). رد الموديل على التوجيه بيترفض ضد allowlist قبل ما يلمس retrieval (الـinjection في التوجيه أقصى ضرره fallback لـNone = بحث داخل scope المسموح). رسالة الرفض المحفوظة نص بتاعنا deterministic مش نص موديل. الـmodel id متفحص ضد قائمة المجانية قبل أي نداء. مافيش أسرار في الـlogs. الـcontext اللي بيشوفه الموديل متفلتر بالصلاحية قبل كده (زي ما كان).
- **Clean Code Guard:** مافيش imports مش مستخدمة (AST pass). اللي اتصلح أثناء الـpass: `chat()` نزلت من ~45 لـ~15 سطر بتقسيم `_require_owned_conversation` / `_start_agent_stream` / `_await_outcome`؛ parameter بتاع اللغة في حالة الاختبار (boolean flag بالمعنى) اتبدّل بحالتين صريحتين فوق helper واحد؛ return type كاذب في `build_graph` اتشال؛ BOM تسل من تعديل PowerShell في سكريبت الاختبار اتشال. المتعلّم عليه: `retrieve` بيرجّع الـchunks كاملة حتى لما تحت الحد (اتخزنت في الـstate للمراجعة/الـaudit بس — الحالة بتتحكم في الرد).
- **Test Guard:** مافيش mocks — داتابيز وOpenRouter حقيقيين، وassertions على الـsaved state (sources/categories/رسايل) مش على الصياغة (Rules 1/10/12). كل حالة بتمسك bug مختلف. الفحوصات الـdeterministic أوفلاين (case 0، تكلفة 0) بتقفل فروع `check_permission` الثلاثة والـparse من غير LLM.

**اللي اتجرّب فعلاً (قبل ما الـquota يخلص) والحالة لكل حاجة:**
- `python -m scripts.test_chat_endpoint` → **4/4 passed**: `/models`، sales سؤال التقسيط → 31 token + حفظ الرد والمصادر (النسختين 2025.1/2026.1) **عبر الـgraph كامل** (توجيه → صلاحية → retrieval → إجابة)، hr سؤال الوحدات → `denied` + حفظ الرفض بالنص الحرفي + header، موديل مدفوع → 422.
- من `test_agent_routing` (تشغيلة كاملة 5/9 بسبب الـquota، وبعدها rerun للحالات الفاشلة): التوجيه اتأكد منه فعلياً في **property_listings (إنجليزي)، company_info_support (إنجليزي)، payment_policies (عربي)، property_listings (عربي)** — المصادر المحفوظة من الـcategory المتوقعة بالظبط. sales سؤال عام → مصادر من الـ3 categories (scope كامل). not-found → الرد الجاهز بالنص + `sources=[]` + محفوظ. regression 422s + framing. الفحوصات الأوفلاين 1/1.
- `load_history` اتراجعت مباشرة على الداتابيز (من غير LLM ولا quota): آخر 10 من 12 بالترتيب، ومحادثة غير موجودة/None → فاضية.
- **متبقي يتأكد لما الـquota يرجع (50/يوم خلاصوا في اليوم ده):** payment_policies بالإنجليزي (محاولة واحدة فشلت برد nemotron فاضي قبل إصلاح ميزانية الـdecision)، company_info_support بالعربي، hr + السؤال العام → company_info_support بس، وmemory end-to-end بالعقد المرن. التشغيلة الكاملة: `python -m scripts.test_agent_routing`.
- **ملاحظة على الموديل المثبّت:** nemotron لسه بيرجع ساعات content فاضي حتى في الـstreaming (خداع Phase 1 المعروف) — بيطلع `error` event ومافيش حفظ (نفس عقد Phase 1). لو تكرر في rerun، التبديل سطر واحد في `CHAT_MODEL` بالسكريبتين (الموديل ده للـاختبار بس، والـdropdown مش متأثر).

**الحالة:** ⚠️ تم جزئياً — الكود كله مكتوب والبنية والفحوصات الـdeterministic + 8 حالات live اتأكدوا (4/4 كاملة في test_chat_endpoint + التوجيه في الاتجاهين بتأكيد جزئي + memory node مباشرة). الباقي محتاج rerun بعد رجوع الـquota اليومي بس، ومفيش أي تغيير كود متوقع له.

## [2026-11-12] — تشخيص وإصلاح الرد الفاضي في مسار الإجابة (respond/streaming)

**تم:**
- **تشخيص بالقياس مش بالتخمين:** سكريبت تشخيصي (`backend/scripts/diagnose_empty_responses.py` — أداة تشخيص قابلة لإعادة الاستخدام، patch وقت التشغيل من غير أي تعديل production code) شغّل حالتي `hr_broad` و`memory` من `test_agent_routing.py` بـ3 محاولات لكل واحدة مع تسجيل الـresponse الخام كامل من OpenRouter. فحص الـquota: ~18 LLM request من الـ50 المجانية في اليوم (الحالتين اتحاولوا بـ2-3 مرات كل واحدة زي ما التشخيص طلب).
- **السبب الجذري المثبت من الـraw response (مش متخمين):** نداء الإجابة (`stream_chat_completion`) بيخلص بـ`finish_reason="length"` و**كل الـ2048 tokens بتاعة الميزانية اتحرقت في reasoning tokens** والـcontent صفر (المقاس: `reasoning_tokens=2048, content=0` على nemotron). السؤال العام/الملتبس (hr_broad) بيحرّض reasoning طويل بشكل شبه حتمي (فشل 2/3 — والمحاولة الناجحة عدّت بالعافية بـ42 token بس للـcontent)، وmemory فشل مرة كـflake لأن الـreasoning بيتراوح 554–1446 token بين التشغيلات.
- **فجوة قائمة من قبل — مش regression:** الـsingle-retry-on-empty في `complete_chat()` بيغطي **قرار الـcategory بس** (نداء non-streaming). نداء الإجابة streaming (`stream_chat_completion`) كان من غير **أي** retry خالص — الإصلاح ده بيقفل فجوة موجودة أصلاً.
- **الإصلاح (Option E المعتمد):**
  1. `openrouter_client.py`: سقف الـanswer call (`_MAX_OUTPUT_TOKENS`) بقى **4096** بدل 2048 — الـdecision call (`_DECISION_MAX_TOKENS=2048`) زي ما هو بالظبط، التغيير scoped للإجابة بس.
  2. `nodes.py` node الـ`respond`: **retry واحد** لو الـstream خلص من غير أي content (نفس فلسفة retry الرد الفاضي في `complete_chat`). المحاولة الأولى الفاضية بتُسجّل في اللوج وبتعاد المحاولة؛ لو المحاولة التانية برضه فاضية → نفس `error` event (`EMPTY_ANSWER_MESSAGE`) زي اليوم بالظبط، من غير أي retry إضافي. الـretry آمن من التكرار لأن المحاولة الفاضية مابعتش ولا token للـstream. الـ`APIError` (rate limit/شبكة) برضه بيفشل فوراً زي قبل — مش بيتعمله retry (scoped للـempty stream بس).
- تشخيص مقارن لرسالتي الخطأ: `MODEL_ERROR_MESSAGE` ("مارجّعش رد" — مسار APIError) و`EMPTY_ANSWER_MESSAGE` ("رجّع رد فاضي" — مسار المحتوى الصفري) حالتين مختلفتين، والفشل المقاس كان التانية.
- **مش يتشغّل في المهمة دي (بقرار موفر للـquota):** مفيش rerun كامل لـ`test_agent_routing.py`. إعادة التحقق من `hr_broad` و`memory` تحديداً بتتم في مهمة منفصلة لما الـquota يسمح (سكريبت التشخيص أو `--only memory,hr_broad` في سكريبت الاختبار).
- Guard passes على التغيير: **Code Security** (مفيش secrets/input جديدة — التغيير منطق retry وسقف tokens بس، مفيش سطح هجوم جديد، اللوج مابيعرضش محتوى حساس) و**Clean Code Guard** (مفيش تعليقات "what"، الـloop محكم، الـconstant باسم معبّر، نفس ستايل الملف، مفيش منطق مكرر — الفحص mirrored مش shared لأن شكلي النداءين مختلف: non-streaming content truthiness مقابل join+strip على parts الـstream).

**ملفات اتعملت/اتعدلت:**
- backend/app/llm/openrouter_client.py — `_MAX_OUTPUT_TOKENS` 2048→4096 (answer call بس) + تعليق السبب بالمقاس الفعلي
- backend/app/agent/nodes.py — retry واحد على الـstream الفاضي في `respond` + `_EMPTY_STREAM_MAX_ATTEMPTS = 2` + تحديث docstring
- backend/scripts/diagnose_empty_responses.py — سكريبت تشخيص خام جديد (أداة، مش production code)
- backend/scripts/test_agent_routing.py — `--only` CLI filter لتشغيل subset من الحالات (للـreruns المقيدة بالـquota)

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- الـretry الاتنين بيتعاملوا مع نفس الميكانيزم لكن في مستويات مختلفة عمداً: `complete_chat` (decision، non-streaming) بيـretry في الـclient، و`respond` (answer، streaming) بيـretry في الـnode — الـstreaming مش ممكن يتغلف بنفس الشكل لأن tokens بتتكتب على الـstream أول ما توصل، والـretry على مستوى الـnode هو اللي بيضمن مافيش تكرار.
- سقف 4096 مازال محدود عمداً (مش مرفوع لانهائي) للحفاظ على الحماية الأصلية ضد الـloop اللي مش بيقفل — والـretry بيغطي الذيل الاحتمالي لو reasoning عدّى 4096.

**الحالة:** ✅ تم — الإصلاح متطبق ومتراجع بالـguard passes؛ التحقق live من الحالتين مؤجل لrerun بعد الـquota.

## [2026-11-13] — إقفال مرحلة الـLangGraph Agent رسمياً (verification + استثناء موثّق وحيد)

**تم:**
- **إقفال التحقق الرسمي لمرحلة الـAgent:** 8/9 حالات في `test_agent_routing.py` بتعدّي بشكل مستقر مع الموديل المثبّت للاختبار `nvidia/nemotron-3.5-lightning:free` — شامل التوجيه باللغتين (إنجليزي + عربي لكل الـ3 categories)، الرفض المحفوظ، السؤال العام لـsales (scope كامل)، سؤال "مش لاقي" بالرد الجاهز، الـregressions (موديل مدفوع/دور غريب → 422)، وحالة الـmemory (دورين في نفس المحادثة) بعد إصلاح ميزانية الـtokens + الـretry.
- **الاستثناء الموثّق (مقبول، مش open-ended):** حالة `hr_broad` — السؤال العام الـ3-أجزاء ("What units are available, how much do they cost, and how can I contact the company?") مع دور hr. التشخيص بالمقياس (سكريبت `diagnose_empty_responses.py` مع raw responses، وسكريبت `diagnose_hr_broad_prompt.py` بدون أي LLM) أثبت إنها **quirk سلوك للموديل ده على شكل السؤال ده تحديداً** (سؤال أجزاؤه الأغلب مش قابلة للإجابة جوه scope الـhr — company_info_support بس)، **مش** مشكلة prompt (أصغر من 2 من الـprompts اللي بتعدّي — ~974 token مقابل 999–1146، 5 chunks من مستند واحد وبدون أي تكرار) **مش** مشكلة retrieval، ومش مشكلة في منطق routing/الصلاحيات نفسه.
- **نطاق الاستثناء:** الحدودة دي scoped للموديل المثبّت للـاختبار **فقط** (`CHAT_MODEL` في سكريبتات الاختبار) — المستخدمين النهائيين بيختاروا بحرية من `GET /models` والموديلات المجانية كلها، ومنطق الـLangGraph (routing + فحص الصلاحية + memory) متأكد صح من الحالات الـ8 التانية + الفحص المباشر لخرج `retrieve_chunks()` لنفس السؤال ده بالظبط في سكريبت التشخيص.
- **تحقيق البديل: مُقفل كتحقيق منتهي (مش معلّق):** 3 محاولات لتجربة موديل بديل للاختبار (`google/gemma-4-31b-it:free`) كلها اتوقفت بعوائق بنية تحتية (infrastructure) خالص — (1) quota يومية مستنفدة، (2) افتراض غلط لنافذة reset (OpenRouter بتعيد الحد عند منتصف الليل UTC مش rolling 24h — مثبت بـ`X-RateLimit-Reset`)، (3) rate limit من الـprovider المشترك upstream لجوجل (`upstream_provider_shared_pool`). صفر requests حقيقية من الموديل المرشح في التلات محاولات، ومفيش أي فشل سلوكي فعلي منه. القرار: وقف البحث عن موديل بديل والاحتفاظ بنيموترون كـ`CHAT_MODEL` للاختبار مع الاستثناء الموثّق.
- **ملاحظة تشغيلية للـquota:** حد الـfree tier بيعدّ عند منتصف الليل UTC (`free_model_daily_requests` في `GET /key` — used/limit/remaining)، والـ429 المرفوضة مش بتستهلك من الحد — يُفحص `remaining > 0` قبل أي rerun عشان مايتبهدلش وقت تشغيلة كاملة على 429.
- **التعليمات للمهام القادمة:** rerun الحالتين (`--only memory,hr_broad`) بعد أي تغيير جوهري في الـretrieval/الـprompts يكون اختياري وليس شرط لإقفال المرحلة؛ حالة `hr_broad` بتتحسّن لو اتغيّر الموديل المستخدم في الاختبار مستقبلاً بقرار صريح، أو لو الـself-check node (المخطط له بين retrieve وrespond) اتضاف في Phase لاحقة.

**ملفات اتعملت/اتعدلت:**
- docs/PROGRESS.md — الإدخال ده بس (مفيش أي تعديل كود في المهمة دي)

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- قرار "قبول الاستثناء بدل مُواصلة البحث" مبني على تلات محاولات infra وقراين التشخيص الكمّي — مش على نفاد الصبر: التشخيص بيوضّح إن الحالة دي بتقيس سلوك موديل على شكل سؤال ملتبس، إنما منطق الـagent (routing/صلاحيات/حفظ) متغطي كامل من الحالات التانية.
- الحالات الـ7 اللي فيها ثقة جزئية من تشغيلات سابقة (test_chat_endpoint 4/4 + توجيه جزئي) اتحوّلت لـ8/9 مثبتة بعد الإصلاحات + reruns في الجلسات دي.

**الحالة:** ✅ تم — مرحلة الـLangGraph Agent (category routing + فحص الصلاحية + memory) **متحقق منها ومقفولة رسمياً** مع استثناء موثّق وحيد (hr_broad على الموديل المثبّت للاختبار)، ومفيش أي عمل مفتوح.

## [2026-11-13] — تحقيق قبل بناء الـAuthentication: الحسابات التجريبية + مسار role/user_id في الـbackend

**تم:**
- **تحقيق استكشافي بسؤالين** (Investigation only — مفيش أي تعديل كود ولا commit):
  1. هل حسابات الـdemo التلاتة موجودة كمستخدمين حقيقيين في Supabase Auth (schema `auth.users`) مش مجرد rows في `profiles`؟ وهل الربط بين الجدولين سليم؟
  2. إزاي `role` و`user_id` بيوصَلوا للـendpoints دلوقتي — body/query params ولا JWT حقيقي؟
- **سكريبت رمي (throwaway)** استعلم `auth.users` + `public.profiles` مباشرة عبر اتصال الـDATABASE_URL الحالي (نفس `get_session_factory()`)، واتمسح بعد الاستخدام (مش في الـversion control).
- **نتيجة 1 — الحسابات التجريبية: ✅ متزرعة صح في Auth:**
  - `auth.users` فيه بالظبط **3 مستخدمين** (من غير أي مستخدم زايد) بإيميلات `admin@reelestate.demo` / `sales@reelestate.demo` / `hr@reelestate.demo`، كلهم `email_confirmed=True` وعندهم `encrypted_password` (قابلين لتسجيل الدخول فعلاً)، اتعملوا 2026-11-09 (seed الـPhase 0).
  - كل واحد فيهم متطابق 1:1 مع row في `profiles` بنفس الـUUID ونفس الـrole المتوقع (admin/sales/hr) — **0 NULL و0 placeholder UUIDs**.
- **نتيجة 2 — بنية الربط الفعلية (مهمة لبناء الـAuth):** schema `profiles` الفعلي هو `(id uuid PK, full_name, role, created_at)` — **مفيش عمود `user_id`**، والربط بـauth.users بيحصل عبر **`profiles.id = auth.users.id`** (نمط Supabase الاعتيادي). ده **مختلف عن المقترح في Tech-Stack.md قسم 3** اللي بيقول `profiles` فيها عمود `user_id` — الملف محتاج تحديث لما الـAuth يتبنى.
- **نتيجة 3 — مسار role/user_id دلوقتي: fake/pre-auth بالكامل (query/body params):**
  - `POST /chat` (backend/app/api/chat.py:59-63): `role: str` و`user_id: UUID` حقول **عادية في الـrequest body** (Model `ChatRequest`) — الـrole بس متحقق منه إنه من الـroles المعروفة (`_role_is_known` validator، chat.py:69-74) لكن مفيش أي إثبات هوية. عمودين عليهما تعليق `TEMPORARY: replace with JWT-derived role/user_id once auth is built` صراحةً.
  - `GET /conversations` و`GET /conversations/{id}` (backend/app/api/conversations.py:24-25,34-35): `user_id` **query parameter** عادي، بنفس تعليق TEMPORARY — يعني أي حد يقدر يقرا محادثات أي موظف لو عرف الـUUID بتاعه (حتى الـ404 ownership check في conversations.py:43 بيعتمد على الـuser_id المُمَرَّر مش على هوية موثّقة).
  - `POST /admin/*`: مش موجودة أصلاً في `backend/app/api/` (الموجود بس `chat.py` و`conversations.py` و`models.py`) — لما تتبنى لازم JWT/role check من أول يوم.
  - **مفيش أي JWT handling في الـbackend خالص:** بحث شامل عن jwt/verify/decode/Authorization مارجعش غير تعليقات/documentation (`supabase_client.py:9` بيفهم JWT كتوضيح لفكرة RLS بس). ملف `app/db/supabase_client.py` بيتحقق من وجود `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` (service_role بيتخطى RLS — للسكريبتات) لكن مش بيستخدم في الـauth flow الإطلاقاً.
- **خلاصة جاهزة لبناء الـAuth (خطوة جاية):** كل الحسابات جاهزة في Auth، و`profiles.id` هو مفتاح الربط؛ المطلوب: (1) التحقق من JWT بتاع Supabase (`Authorization: Bearer <access_token>`) بفحص signature + expiry مش decode بس، (2) استخراج `user_id` من الـtoken مش من الـclient، (3) `role` يتقرا من `profiles` على السيرفر (مش من الـclient زي دلوقتي — دلوقتي أي حد يقدر يبعت `role=admin` في الـbody وياخد scope الـadmin في /chat).

**ملفات اتعملت/اتعدلت:**
- docs/PROGRESS.md — الإدخال ده بس (سكريبت الاستعلام كان رمي واتمسح بعد الاستخدام)

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- الانحراف عن Tech-Stack.md قسم 3 (profiles بدون user_id، والربط عبر id) مسجل هنا عشان يتحدّث الملف أو يتظبط المرجعية وقت بناء الـAuth.
- ملاحظة أمان تشغيلية: الـRLS لسه مش مطبّق حسب تعليق `retrieval.py:8` (الفلترة الحالية كود تطبيق بس) — التحقق من الـJWT لما يتبنى لازم يتعامل مع النقطة دي في نفس المرحلة.

**الحالة:** ✅ تم — تحقيق مكتمل بالأدلة: الحسابات جاهزة ومتزروعة صح في Auth، ومسار role/user_id الحالي fake/pre-auth بالكامل (body/query params بدون JWT) — جاهزين لبدء بناء الـAuthentication على أساس واقعي مش مفترض.

## [2026-11-13] — تصحيح توثيقي: وصف جدول `profiles` في Tech-Stack.md بقى مطابق للـschema الفعلي

**تم:**
- تصحيح توثيق بس (documentation correction) — **مفيش أي تغيير كود ولا في schema.sql**.
- **اللي كان غلط:** Tech-Stack.md قسم 3 (جدول "الجداول المقترحة") كان بيوصف `profiles` بعمود `user_id` وعمود `email`. الـschema الفعلي (`backend/app/db/schema.sql:10-15`) والتحقيق المباشر على الداتابيز الحقيقية بيثبتوا إن الجدول هو `(id uuid PK references auth.users(id) on delete cascade, full_name, role, created_at)` — **مفيش عمود user_id خالص** (مفتاح الربط هو `profiles.id = auth.users.id` نفسه)، ومفيش عمود email (الإيميل عايش في `auth.users` بس).
- **بقى يقول إيه:** صف `profiles` في Tech-Stack.md دلوقتي بيقول `id (PK متطابق مع auth.users.id — مش عمود user_id)، role، full_name، created_at — الإيميل في auth.users مش هنا (schema.sql الفعلي هو المرجع)`. باقي مراجع `user_id` في الملف (جدول `conversations` مثلاً) صح ومتزروعة — `conversations.user_id references profiles(id)` فعلاً (schema.sql:55).
- **ليه مهم قبل الـAuth:** أي استعلام سيتبنى على `profiles.user_id` هيضرب `UndefinedColumn` فوراً — التصحيح بيمنع إن مرحلة الـAuthentication تبني كود على عمود مش موجود (كان متسجل كملاحظة مفتوحة في إدخال التحقيق قبل ده، واتقفل دلوقتي).

**ملفات اتعملت/اتعدلت:**
- docs/Tech-Stack.md — صف واحد في جدول قسم 3 بس (الصف اللي بيوصف `profiles`)
- docs/PROGRESS.md — الإدخال ده

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- تصحيح الـ`email` في نفس الصف دخل ضمن نطاق "وصف جدول profiles" لأن الادعاءين الغلطكان (user_id وemail) في نفس السطر — سِبَهم في توثيق مغلوط هيضلّل مبنى الـAuth بنفس الطريقة.

**الحالة:** ✅ تم — التوثيق بقى مطابق للـschema الفعلي والملاحظة المفتوحة من إدخال التحقيق اتقفلت.

## [2026-11-14] — المرحلة: Authentication كامل — JWT verification + RLS + واجهة الدخول

**تم:**
- **الـbackend** — استبدال shortcut الـTEMPORARY (role/user_id من الـrequest) بمصادقة حقيقية:
  - موديول `app/auth/`: التحقق من JWT بتاع Supabase (JWKS الأول مع cache، وfallback لـHS256 على `SUPABASE_JWT_SECRET` لو الـJWKS مش متاح)، ورفض `aud != "authenticated"`. `get_current_user` بيقرا الـuser_id من الـ`sub` الموقّع بس، والـrole/full_name من `profiles` على السيرفر. `require_admin` للـendpoints الإدارية (Phase 3).
  - `GET /me` جديد (محمي) بيرجع `{user_id, role, full_name}` — مصدر الـprofile في الواجهة.
  - `POST /chat`: الـauth الأول قبل أي فحص تاني (بدون Authorization → 401 حتى لو الموديل مدفوع)، ومفيش role/user_id في الـbody خالص؛ الـownership والـagent state بيتقروا من الـidentity المتحقق منها.
  - `GET /conversations` + `GET /conversations/{id}`: الـuser_id من الـtoken (مفيش query param) — كل موظف شايف محادثاته هو بس، و404 موحد لمش موجودة/بتاعة حد تاني.
  - CORS: `Authorization` مسموح في الـheaders.
- **الـRLS** — `migrations/002_rls_policies.sql` اتنفّذت على الداتابيز الحقيقية: RLS على profiles/documents/chunks/conversations/messages/eval_runs (وaudit_logs بحارس لوجودها — الجدول لسه مش متإنشا)، وpolicies مطابقة لمصفوفة الصلاحيات + ownership، مع `get_my_role()` SECURITY DEFINER لمنع الـrecursion. Negative control: الـanon key مرفوض على كل الجداول. ملاحظة معتمدة: اتصال الـbackend بـPostgres بيتخطى RLS بالتصميم (owner) — الحماية الفعلية كود الـapp، والـRLS ضد الوصول المباشر بالـanon key.
- **الـfrontend** — واجهة الدخول + إدارة الجلسة: صفحة `/login` (bilingual en/ar، tokens الـDesign-System)، `@supabase/supabase-js` للـlogin والـsilent refresh و`onAuthStateChange`، `authStore` (Zustand + persist — للعرض بس)، `lib/api/client.ts` (fetch wrapper بـAuthorization + refresh قبل الخلاص + redirect لصفحة الدخول على فشل الـrefresh أو 401)، `RequireAuth`/`RequireAdmin` (حماية عرض بس)، components/ui (Button/Input من الـtokens)، globals.css بتوكنز Modern Slate Blue (light+dark)، root layout بـ[locale] (النمط الرسمي للـi18n في Next 16) و`global-not-found.tsx`، وplaceholder لـ/chat بيأكد المسار كامل شغال.
- **الاختبارات** — `scripts/demo_auth.py` (password grant حقيقي للحسابات الـdemo) + إعادة كتابة `test_chat_endpoint.py` و`test_agent_routing.py` على Bearer tokens: النتيجة 5/5 و8/9 (الفشل الوحيد hr_broad — نفس quirk الموديل الموثق يوم 2026-11-13، مش كود). بلاش تكلفة: offline deterministic + regressions (موديل مدفوع → 422، بدون Authorization → 401).
- **الـskill passes الإلزامية** — clean-code-guard على كل الكود الجديد (نضيف — مفيش تعديلات)، web-design-guidelines على الـlogin UI (اتصلحت: radius tokens كانت self-reference في @theme، وcolor-scheme، وtheme-color، وname/autocomplete للحقول، وfocus-visible للـInput)، ux-writing على رسايل الدخول (ellipsis في حالات التحميل + translate="no" للـwordmark)، test-guard على السكريبتات (نضيف).

**ملفات اتعملت/اتعدلت:**
- backend/app/auth/__init__.py، backend/app/auth/verification.py، backend/app/auth/dependencies.py — الجديدة (المصادقة)
- backend/app/api/me.py — الجديدة (GET /me)
- backend/app/api/chat.py، backend/app/api/conversations.py، backend/app/main.py — إزالة role/user_id من الـrequest + الـauth في كل endpoint
- backend/app/db/migrations/002_rls_policies.sql — الجديدة (اتنفّذت على الداتابيز الحقيقية)
- backend/.env.example — أضيف `SUPABASE_JWT_SECRET=` (اختياري)
- backend/scripts/demo_auth.py — الجديدة (login للحسابات الـdemo)
- backend/scripts/test_chat_endpoint.py، backend/scripts/test_agent_routing.py — إعادة كتابة على Bearer tokens
- frontend/app/[locale]/layout.tsx، app/[locale]/(auth)/login/page.tsx، app/[locale]/(chat)/chat/page.tsx، app/[locale]/(admin)/layout.tsx، app/global-not-found.tsx، app/globals.css — الجديدة (الـrouting والـlayout والصفحات والتوكنز)
- frontend/features/auth/{api/supabase.ts، api/me.ts، types.ts، hooks/useAuth.ts، components/LoginForm.tsx، components/RequireAuth.tsx، components/ChatPlaceholder.tsx، components/SessionSync.tsx} — الجديدة
- frontend/store/authStore.ts، frontend/lib/api/client.ts، frontend/lib/utils.ts، frontend/components/ui/{Button.tsx، Input.tsx}، frontend/i18n/{routing.ts، request.ts}، frontend/messages/{en.json، ar.json}، frontend/next.config.ts، frontend/.env.local(.example) — الجديدة
- docs/Tech-Stack.md — قسم 6 اتكتب من جديد بالقرارات الخمسة والـtrade-offs، قسم 2 فيه GET /me وتعليم الحماية، قسم 1 فيه supabase-js، قسم 11 فيه الـJWT secret
- docs/PROGRESS.md — الـentry ده

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:**
- **الخمس قرارات الـarchitecture** (موثقة بالكامل في Tech-Stack.md قسم 6): (1) JWKS الأول + HS256 fallback، (2) الـrole دايماً من profiles على السيرفر، (3) RLS طبقة ثانوية والـapp code هو الحماية الفعلية، (4) GET /models عامة عمداً، (5) silent refresh + redirect-on-401. الـrate limiting متأجل قرار (خارج المرحلة).
- **audit_logs مش موجود في الداتابيز الحقيقية** (جدول Phase 3) — الـmigration عملت حارس `to_regclass` بدل ما تكسر.
- **next-intl/plugin مااتاستخدمش**: native binding بتاع @swc/core بايظ في البيئة دي (LoadLibraryExW بيفشل حتى بعد إعادة التثبيت) — الـalias بتاع `next-intl/config` → `i18n/request.ts` اتعمل يدوي في next.config.ts. **متعملش رجوع لـcreateNextIntlPlugin**.
- **`instant = false` على layout الـ[locale]** — blocking route مقصود: الـlayout بيقرا الـlocale من الـparams للـhtml lang/dir، وcacheComponents كان بيرفض prerender من غيرها.
- **UX Writing kit مش موجود محلياً** (voice-tone.md مش مثبت — KIT_MISSING) — الرسايل اتكتبت على أساس مبادئ الـskill المدمجة. لو الـkit اتثبت، يعاد فحص الرسايل عليه.
- **hr_broad لسه بيفشل** — نفس quirk الموديل الموثق يوم 2026-11-13 (سلوك موديل، مش كود) — بيتقاس في الـgolden dataset بتاع RAGAS في Phase 4.
- **VerifyAuth = حماية عرض بس** — مكتوبة في التعليقات وفي قسم 6 إن التفويض الفعلي على الـbackend.
- فحص quota قبل تشغيل الاختبارات: 50/50 متاحة (بتتصفّر كل نص الليل UTC) — الاختبارات استهلكت ~24.

**الحالة:** ✅ تم — المصادقة كاملة (backend + RLS + frontend) والاختبارات عايشة على الـBearer tokens والـdocs متحدثة. فحص إضافي مقترح في المتصفح يدوي (login → /chat بـالحسابات الـdemo) لما تستريح مع الـUI.
