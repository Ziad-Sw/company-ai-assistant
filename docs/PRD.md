# PRD — Company AI Assistant

> **وصف الملف:** هذا هو الـProduct Requirement Document لمشروع "Company AI Assistant" — مساعد ذكي داخلي لموظفي **Reel Estate** (شركة عقارات وهمية بالكامل، الاسم مقصود كتورية على "Real Estate")، بيجاوب من قاعدة بيانات الشركة باستخدام RAG وAgent بصلاحيات حسب الدور. الملف ده بيحدد *إيه* هنبني وليه — التفاصيل التقنية (الـstack، البنية، الكود) في `Tech-Stack.md`.

---

## 1. Overview & Purpose

**Company AI Assistant** مشروع Portfolio في تخصص Agentic AI Engineering. الهدف منه إثبات القدرة على بناء نظام AI كامل (مش tutorial) يجمع بين: واجهة شات حقيقية، RAG بالكود، Agent بيتخذ قرارات (اختيار category، فلترة حسب الصلاحية)، وAuthentication بأدوار، وEvaluation فعلي.

## 2. Problem Statement

في أي شركة، الموظف الجديد أو حتى القديم بيضيّع وقت وهو بيدور على معلومة (سياسة إجازات، سعر وحدة، خطة تقسيط) في مستندات متفرقة أو بيسأل زميل/مدير. **Company AI Assistant** بيحل المشكلة دي بمساعد واحد كل موظف يسأله بلغته (عربي أو إنجليزي)، ويرد بدقة من مصدر موثوق، وما يعرضش معلومة الموظف مش مصرح له بيها.

## 3. Users & Roles

| الدور | يشوف إيه |
|---|---|
| **Sales** | `property_listings` + `payment_policies` + `company_info_support` |
| **HR** | `company_info_support` فقط |
| **Admin** | كل الـcategories + إدارة المستندات + إدارة حسابات الموظفين |

مفيش Sign-up عام. الحسابات بتتعمل من الـAdmin أو seeded كـdemo accounts (تفاصيلها في `demo-accounts.md`).

## 4. Simulated Company Profile

**اسم الشركة:** Reel Estate (وهمية بالكامل، تورية على "Real Estate").
**القطاع:** عقارات (Real Estate).

**الـ3 Categories لبيانات الشركة:**

| Category | المحتوى |
|---|---|
| `property_listings` | الوحدات المتاحة — نوع، مساحة، سعر، موقع، حالة التوفر |
| `payment_policies` | خطط التقسيط، شروط الحجز، سياسة الإلغاء، مستندات العقد |
| `company_info_support` | عن الشركة، الصيانة بعد التسليم، التواصل، الأسئلة الشائعة |

البيانات نفسها هتتولّد (بمراجعة يدوية) وتُخزّن بصيغ متنوعة (PDF, DOCX, Markdown, جداول) عشان تغطي سيناريوهات الـingestion المختلفة.

## 5. Core Features

| # | Feature | وصف مختصر |
|---|---|---|
| 1 | **Login** | دخول بالإيميل والباسورد، تحديد الـrole تلقائياً من الجلسة |
| 2 | **Chat** | السؤال والجواب — RAG + Agent، بما فيها HITL approval للحالات الحساسة |
| 3 | **Conversation History (Sidebar)** | قائمة بالمحادثات السابقة، رجوع لأي محادثة قديمة |
| 4 | **Model Selection (Dropdown)** | اختيار موديل من الموديلات المجانية المتاحة في OpenRouter |
| 5 | **Document Management (Admin only)** | صفحة مستقلة لإدارة knowledge base الشركة بالكامل: عرض كل المستندات، رفع جديد، تعديل الـcategory، استبدال بنسخة محدّثة، تعطيل/حذف، إعادة معالجة، وسجل من رفع إيه وإمتى |
| 6 | **Add Employee (Admin only)** | إنشاء حساب موظف جديد بتحديد role، وتوليد إيميل/password تلقائي |

## 6. Agent Behavior

الـagent مبني على LangGraph (التفاصيل الكاملة في `Tech-Stack.md`). المنطق المختصر:

1. الموظف يسأل سؤال
2. الـagent (LLM) يقرر السؤال خاص بأنهي category — **قرار agentic**
3. فحص صلاحية الـrole مقابل الـcategory — **كود ثابت (deterministic)، مش قرار LLM**
4. لو مسموح: تنفيذ `search_knowledge_base(query, category)` → إجابة بمصادر (اسم المستند + القسم)
5. لو مش مسموح: رفض **واضح ومباشر** يسمّي السبب (مش رد غامض زي "مش لاقي المعلومة")
6. لو مفيش معلومة أصلاً في البيانات: الرد "مش لاقي ده في بيانات الشركة" — مش يخترع إجابة

**الـTool الأساسي لـPhase 1:** `search_knowledge_base(query, category)`.

## 7. Data & Metadata Schema

كل chunk في الـknowledge base معاه metadata:

| Field | الوصف |
|---|---|
| `doc_id`, `title` | هوية المستند |
| `category` | واحدة من الـ3 (`property_listings` / `payment_policies` / `company_info_support`) |
| `section`, `page` | موقع الـchunk جوه المستند |
| `version`, `updated_at` | للتعامل مع مستندات متضاربة (قديم/جديد) |
| `language` | عربي/إنجليزي |

**Chunking:** heading-aware، حوالي 500-800 token، overlap 10-15%.

**حالات اختبار لازم تتصمم من البداية:**
- مستندين متضاربين (نسخة قديمة وجديدة لنفس السياسة)
- أسئلة مالهاش إجابة في البيانات أصلاً
- أسئلة محتاجة أكتر من مستند عشان تتجاوب

## 8. Non-Functional Requirements

- **اللغة:** دعم كامل عربي/إنجليزي — الموظف يسأل بأي لغة والنظام يرد بنفس لغة السؤال
- **قيود الموديلات المجانية:** OpenRouter (50 request/يوم بدون شراء)، فلازم caching للإجابات وقت التطوير وقائمة fallback models
- **الخصوصية:** بيانات وهمية فقط — الموديلات المجانية ممكن تسجل الـprompts
- **الأداء:** رد الـAI لازم يبان كـstreaming (مش ينتظر الموظف الإجابة كاملة)

## 9. Evaluation & Success Metrics

- **Golden dataset:** 30-50 سؤال مع المصدر المتوقع لكل سؤال
- **RAGAS:** قياس faithfulness، answer relevancy، context precision/recall
- **Permission tests:** التأكد إن كل role بيتفلتر صح (موظف HR محدش يقدر يجيبله بيانات `property_listings`)
- **تقرير أرقام قبل وبعد أي تحسين** في الـretrieval أو الـprompting

## 10. User Flow

### 10.1 Login
```
يدخل الموظف على رابط التطبيق
→ صفحة Login (إيميل + password)
→ تسجيل دخول ناجح → يتحول لصفحة Chat
→ فشل (بيانات غلط) → رسالة خطأ واضحة، يحاول تاني
```

### 10.2 Chat (الأساسي — شامل HITL)
```
الموظف يفتح صفحة Chat (محادثة جديدة أو مستمرة من الـsidebar)
→ يكتب سؤاله (عربي أو إنجليزي) ويبعت
→ الرد يبدأ يظهر streaming
→ [جوه الخلفية]: الـagent يحدد category → فحص صلاحية → تنفيذ الأداة أو رفض
→ لو السؤال يحتاج إجراء حساس (مثال مستقبلي: طلب معلومة حساسة جداً):
    → الموظف يشوف رسالة "محتاج موافقة قبل ما أكمل" + زرار Approve/Cancel
    → الموافقة → الإجراء يكمل | الرفض → يتوقف الإجراء
→ الرد يظهر كامل مع مصدره (اسم المستند)
→ المحادثة تتحفظ تلقائياً في الـsidebar
```

### 10.3 Conversation History (Sidebar)
```
الموظف يفتح الـsidebar (مفتوح افتراضياً زي Claude.ai)
→ يشوف قائمة محادثاته السابقة (الأحدث فوق)
→ يضغط على محادثة قديمة → تفتح بكل رسائلها
→ يقدر يبدأ محادثة جديدة من زرار "+ New Chat"
```

### 10.4 Model Selection
```
الموظف يضغط على الـdropdown جنب مربع الكتابة
→ يشوف قائمة الموديلات المجانية المتاحة حالياً (تُجلب ديناميكياً من OpenRouter)
→ يختار موديل → يتحفظ كتفضيل للمحادثة الحالية
→ لو موديل اختفى من القائمة المجانية فجأة: رسالة واضحة + fallback تلقائي لموديل تاني متاح
```

### 10.5 Document Management (Admin)

صفحة مستقلة (`/admin/documents`) بتدير دورة حياة المستند كاملة، مش رفع بس:

**أ) عرض وفلترة**
```
الـAdmin يفتح Admin → Documents
→ يشوف قائمة كل المستندات: الاسم، category، تاريخ آخر تحديث، الحالة (Active/Inactive/Processing/Failed)، مين رفعه
→ يقدر يفلتر حسب category أو يبحث بالاسم
```

**ب) رفع مستند جديد**
```
يضغط "Upload Document"
→ يرفع الملف (PDF/DOCX/Markdown) ويحدد الـcategory يدوياً
→ النظام يعرض حالة المعالجة لحظياً (Extracting → Chunking → Embedding → Done)
→ فشل في أي خطوة: رسالة خطأ واضحة تحدد أنهي خطوة فشلت + زرار "إعادة المحاولة"
→ نجاح: المستند يظهر "Active" وجاهز للاسترجاع فوراً
```

**ج) تعديل مستند موجود**
```
يضغط على مستند من القائمة
→ يقدر: يغيّر الـcategory | يستبدله بنسخة جديدة (version جديد، النسخة القديمة تتحفظ في السجل مش تتمسح) | يعطّله مؤقتاً (Inactive، مش بيظهر في الاسترجاع بس لسه موجود) | يحذفه نهائياً (تأكيد إلزامي قبل الحذف) | يطلب إعادة معالجة (Reprocess) لو الـembedding فشل أو عايز يغيّر إعدادات الـchunking
```

**د) Audit Trail**
```
كل عملية (رفع/تعديل/حذف/تعطيل) بتتسجل: مين عملها + إمتى
→ متاحة كسجل بسيط تحت كل مستند، مش صفحة منفصلة في Phase الأول
```

### 10.6 Add Employee (Admin)
```
الـAdmin يفتح صفحة Admin → Employees
→ يضغط "Add Employee"
→ يكتب الاسم + يختار الـrole (Sales/HR/Admin)
→ النظام يولّد الإيميل تلقائي (الاسم@reelestate.demo) + password مؤقت
→ الكريدنشيالز تتعرض مرة واحدة بس على الشاشة (مع تنبيه "احفظها دلوقتي، مش هتظهر تاني")
→ الـAdmin يبعتها يدوياً للموظف
→ الموظف الجديد يظهر في قائمة الموظفين
```

## 11. Phased Roadmap

بناءً على 10-20 ساعة متاحة أسبوعياً:

| Phase | المحتوى | المخرَج |
|---|---|---|
| **0** | إعداد: repo، الـfolder structure، Supabase project، الـschema، توليد بيانات الشركة الوهمية | بيئة شغالة وبيانات جاهزة |
| **1** | RAG MVP: ingestion، chunking، embeddings، retrieval بالـcategory، `/chat` بـstreaming، UI أساسي (شات + sidebar + model dropdown)، Login بالأدوار الثلاثة | سؤال وجواب بمصادر، permission filtering شغال |
| **2** | Agent كامل بـLangGraph: category routing، query rewriting، self-check للإجابة، memory للمحادثة، HITL interrupt | agent بقرارات agentic حقيقية |
| **3** | Document Management + Add Employee (واجهات الـAdmin) | إدارة كاملة من غير تدخل يدوي في الداتابيز |
| **4** | Evaluation + Observability: golden dataset، RAGAS، tracing | تقرير أرقام قبل/بعد |
| **5** | Production polish: guardrails، نشر live، README + architecture diagram + demo video | مشروع جاهز للـPortfolio |

## 12. Risks & Open Assumptions

- **Supabase pause:** المشروع الـfree بيتعمله pause بعد أسبوع خمول — لازم إعادة تفعيل قبل أي demo/إنترفيو
- **حد OpenRouter اليومي:** 50 request/يوم ممكن يخلص بسرعة وقت التطوير والاختبار — الحل: caching + fallback models + بيانات اختبار صغيرة
- **تغيّر الموديلات المجانية:** بتتغير وتختفي بدون إنذار — الـdropdown لازم يتعامل مع الحالة دي بشكل مرن
- **دقة اختيار الـcategory من الـagent:** محتاج اختبار فعلي على أسئلة غامضة (سؤال ممكن يخص أكتر من category)
