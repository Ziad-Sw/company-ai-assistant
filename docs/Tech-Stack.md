# Tech Stack — Company AI Assistant

> هذا الملف بيوثّق الـtechnology stack الكامل لمشروع "Company AI Assistant" — مساعد ذكي داخلي لموظفي شركة real estate وهمية، بـRAG وAgent وصلاحيات حسب الدور. أي موديل/أداة AI بتشتغل على الكود لازم تقرأ الملف ده الأول قبل أي تعديل.

---

## 1. Frontend

| التقنية | الاستخدام |
|---|---|
| **Next.js (React)** | بُني من الصفر (مش من template) — App Router |
| **TypeScript** | إلزامي لكل الكود |
| **Tailwind CSS** | الـstyling الأساسي، مبني على التوكنز في `Design-System.md` |
| **Zustand** | state management — `authStore` (role, user, token)، `chatStore` (active conversation, streaming buffer) |
| **next-intl** | دعم اللغتين عربي/إنجليزي |
| **SSE / Fetch Streaming** | لعرض رد الـAI بشكل streaming زي ChatGPT/Claude |

الواجهة بتتبنى بمنطق شبيه بـClaude.ai (شات + sidebar لتاريخ المحادثات + dropdown لاختيار الموديل)، لكن بألوان ومطابقة بصرية خاصة بالمشروع — راجع `Design-System.md`.

## 2. Backend

| التقنية | الاستخدام |
|---|---|
| **FastAPI (Python)** | الـAPI الأساسي |
| **Uvicorn** | الـserver |
| **Pydantic** | تعريف الـschemas والـstructured outputs |
| **SQLAlchemy + psycopg** | الاتصال بـPostgres (Supabase) |
| **python-dotenv** | قراءة الـsecrets من `.env` (مش من ملفات تتترفع على GitHub) |

**Endpoints الأساسية:**
- `POST /chat` — streaming، بيعدي على الـLangGraph agent
- `GET /conversations` — تاريخ محادثات الموظف الحالي
- `GET /models` — قائمة الموديلات المجانية المتاحة من OpenRouter (ديناميكي)
- `GET /admin/documents` — قائمة كل المستندات، مع فلترة بالـcategory والبحث بالاسم
- `POST /admin/documents` — رفع مستند جديد (Admin فقط)
- `PATCH /admin/documents/{id}` — تعديل category / تعطيل (Inactive) / تفعيل
- `POST /admin/documents/{id}/replace` — استبدال بنسخة جديدة (version جديد، القديم يتحفظ)
- `POST /admin/documents/{id}/reprocess` — إعادة extract/chunk/embed
- `DELETE /admin/documents/{id}` — حذف نهائي
- `GET /admin/documents/{id}/audit` — سجل من عدّل/رفع/حذف وإمتى
- `POST /admin/employees` — إنشاء حساب موظف جديد (Admin فقط)، بيولّد إيميل + password مؤقت

## 3. Database & Vector Store

**Supabase (Postgres + pgvector + Auth)** — مجاني، بيدّي الداتابيز والمصادقة في مكان واحد.

> ⚠️ ملاحظة مهمة: مشروع Supabase الـFree بيتعمله **pause بعد أسبوع من عدم النشاط** (البيانات بتفضل، لازم إعادة تفعيل يدوي). لازم تتراعى دي وقت الـdemo/الإنترفيو.

**الجداول المقترحة:**

| الجدول | المحتوى |
|---|---|
| `profiles` | user_id، role (sales/hr/admin)، full_name، email |
| `conversations` | id، user_id، title، created_at |
| `messages` | id، conversation_id، role (user/assistant)، content، created_at |
| `documents` | id، title، category، access roles المسموحة، version، status (Active/Inactive/Processing/Failed)، uploaded_by، created_at |
| `chunks` | id، document_id، content، embedding (vector)، metadata (jsonb: category, section, page) |
| `eval_runs` | id، golden_question، expected_source، actual_answer، score، created_at |
| `audit_logs` | id، actor_id (مين عمل العملية)، action (upload/edit/replace/deactivate/delete/reprocess)، target_type (document/employee)، target_id، created_at |

**الـ3 Categories المعتمدة لبيانات الشركة:**

| Category | Sales | HR | Admin |
|---|:---:|:---:|:---:|
| `property_listings` | ✅ | ❌ | ✅ |
| `payment_policies` | ✅ | ❌ | ✅ |
| `company_info_support` | ✅ | ✅ | ✅ |

**طبقتين حماية للصلاحيات:** (1) فحص deterministic داخل الـLangGraph node قبل تنفيذ أي tool، (2) Row Level Security (RLS) في Postgres نفسه — حتى لو حصل bug في الكود، الداتابيز ترفض البيانات مش مصرح بيها.

## 4. LLM & Embeddings

| | الاختيار | التفاصيل |
|---|---|---|
| **LLM (المحادثة والـAgent)** | **OpenRouter** — الموديلات المجانية فقط | عن طريق OpenAI-compatible client؛ الـdropdown بيتملا ديناميكياً من الـmodels API ويعرض المجاني بس. حد: 50 request/يوم (20/دقيقة) بدون شراء، 1000/يوم بعد شراء $10 مرة واحدة (اختياري، مؤجل القرار) |
| **Embeddings** | **Gemini embedding API** (`gemini-embedding-001`) | مجاني، متعدد اللغات (بيخدم دعم عربي/إنجليزي) — **منفصل تماماً عن الـLLM**: الـembeddings بتحوّل النص لـvectors للبحث، مش بتولّد ردود |

⚠️ مش كل الموديلات المجانية في OpenRouter بتدعم tool calling — لازم التأكد من صفحة الموديل قبل إضافته للـdropdown.

## 5. Agent Orchestration

| الأداة | الدور |
|---|---|
| **LangGraph** | الـorchestration الكامل: الـstate (هوية الموظف، role، الـconversation)، الـconditional routing (فحص الصلاحية قبل أي tool)، HITL interrupts (موافقة بشرية لإجراءات حساسة)، الـmemory بين الرسائل |
| **LangChain `create_agent`** | يُستخدم **جوه nodes الـLangGraph** تحديداً — الـharness الجاهز للـtool-calling بدل كتابة ReAct loop يدوي. مبني رسمياً فوق LangGraph، مش بديل له |

**الـTool الأساسي:** `search_knowledge_base(query, category)` — الـagent هو اللي بيختار الـcategory المناسبة بناءً على فهمه لسؤال الموظف. ده اللي بيحوّل المشروع من RAG عادي لـAgentic فعلي.

**منطق الفلو المختصر:**
```
سؤال → الـagent يحدد category (قرار agentic)
     → فحص صلاحية الـrole (كود ثابت، مش قرار LLM)
     → مسموح؟ تنفيذ search_knowledge_base → إجابة
     → مش مسموح؟ رفض واضح ومباشر يوضح السبب (مش رد غامض)
```

## 6. Authentication & Roles

- **Supabase Auth** — JWT-based
- **مفيش Sign-up عام** — الموظف ميعملش حساب لنفسه
- **Admin بس يقدر يضيف موظفين**: يكتب الاسم + الـrole، النظام يولّد الإيميل تلقائي (`الاسم@reelestate.demo` — دومين وهمي، مش gmail.com) وpassword مؤقت، بيتعرض مرة واحدة بس بعد الإنشاء
- **3 حسابات Demo جاهزة** (seeded من Phase 0): Sales، HR، Admin — موثّقة في `docs/demo-accounts.md`
- **الأدوار:** `sales`، `hr`، `admin` — متخزنة في جدول `profiles`، وبتتحط في الـLangGraph state من أول خطوة (structured state، مش نص في الـprompt)

## 7. Evaluation & Observability

| الأداة | الاستخدام |
|---|---|
| **RAGAS** | قياس جودة الـRAG: faithfulness، answer relevancy، context precision/recall — على golden dataset (30-50 سؤال) |
| **Langfuse أو LangSmith** | tracing لكل خطوة في الـagent (يتحدد لاحقاً أيهم، حسب حدود الـfree tier وقتها) |

## 8. Deployment

**Live deployment** (رابط شغال، مش Docker محلي بس):
- Frontend: Vercel
- Backend: Railway أو Render
- Database: Supabase (hosted أصلاً)

## 9. Folder Structure

بنية **Feature-based**: كل feature قائم بذاته بكل حاجاته، والمشترك فقط في `/components`.

```
company-ai-assistant/
├── frontend/
│   ├── app/
│   │   /[locale]
│   │     /(auth)/login/page.tsx
│   │     /(chat)/chat/page.tsx
│   │     /(chat)/chat/[conversationId]/page.tsx
│   │     /(admin)/admin/documents/page.tsx
│   │     /(admin)/admin/employees/page.tsx
│   ├── features/
│   │   /auth            → components, hooks (useAuth, useSession), api, types.ts
│   │   /chat             → MessageBubble, ChatInput, ModelDropdown, StreamingIndicator; useChatStream
│   │   /conversations     → ConversationList, ConversationItem (sidebar history)
│   │   /admin-documents    → DocumentTable, DocumentFilters, DocumentUploader, CategoryPicker, VersionHistoryModal, AuditLogPanel
│   │   /admin-employees     → EmployeeForm, GeneratedCredentials
│   ├── components/
│   │   /ui              → Button, Dropdown, Avatar, Modal (من design-system.md)
│   │   /shared            → Sidebar, Header, LanguageSwitcher
│   ├── lib/
│   │   /api/client.ts    → fetch wrapper + auth token attach
│   │   utils.ts            → cn() helper
│   ├── store/
│   │   authStore.ts       → Zustand + persist
│   │   chatStore.ts        → Zustand (active conversation, streaming)
│   └── messages/            → en.json, ar.json (next-intl)
│
├── backend/
│   ├── app/
│   │   ├── api/            → /chat, /conversations, /models, /admin/documents, /admin/employees
│   │   ├── agent/            → LangGraph graph, nodes, tools (search_knowledge_base)
│   │   ├── rag/                → chunking, embeddings, retrieval
│   │   ├── db/                   → SQLAlchemy models, Supabase client
│   │   ├── auth/                   → role checks, JWT verification
│   │   └── eval/                     → RAGAS scripts, golden dataset
│   └── tests/
│
├── data/                        → fake real estate company docs (raw + processed)
└── docs/                          → PRD.md, Tech-Stack.md, Design-System.md, demo-accounts.md
```

**القاعدة الأساسية (إلزامية):** أي component خاص بـfeature معين يروح جوه `features/[module]/components/`، مش `/components/[module]/`. الـ`/components/` ده للمشترك بين أكتر من موديول فقط.

## 10. Skills — تعليمات الاستخدام الإلزامية

الـSkills دي مش خاصة بأداة معينة — أي موديل/IDE بيشتغل على الكود (Cursor، Claude Code، غيرهم) لازم يطبّقها في المرحلة المناسبة. **القاعدة العامة: كل skill ليها وظيفة محددة، متستخدمش skill في غير سياقها.**

| Skill | يتفعّل إمتى | على إيه بالظبط |
|---|---|---|
| **Code Security** | **إلزامي** مع أي كود بيتعامل مع: user input، authentication، database queries، file operations، network requests، أو infrastructure config | خصوصاً: الـauth flow (login، JWT verification)، أي endpoint بيستقبل بيانات من المستخدم، أي SQL/ORM query، الـRLS policies |
| **Clean Code Guard** | بعد ما يتكتب/يتعدّل/يتريفاكتور أي كود production، **قبل** ما يتعرض أو يتعمله commit | كل كود Python (backend) وTypeScript (frontend) — Clean Code، SOLID، DRY، KISS، YAGNI |
| **Test Guard** | بعد ما تتكتب/تتعدّل أي tests، **قبل** commit | pytest للـbackend، Jest/Vitest للـfrontend |
| **Code Review** | وضع مراجعة عام — يُستخدم بدل التعديل المباشر لما المطلوب "مراجعة" مش "تنفيذ" | أي مرحلة فيها مراجعة كود قبل الدمج |
| **Frontend Design** | وقت بناء أو تعديل أي UI component جديد | كل مكونات `/components/ui` و`/features/*/components` |
| **UX Writing** | وقت كتابة أي نص ظاهر للمستخدم | رسائل الأخطاء، الـempty states، نص الأزرار، الـnotifications، رسالة رفض الصلاحية |
| **Web Design Guidelines** | بعد بناء أي صفحة/component، **قبل** التسليم | مراجعة الـaccessibility ومطابقة معايير الواجهة |

**ترتيب الاستخدام في أي مهمة تطوير:**
1. وقت الكتابة: **Code Security** (لو الكود حساس) + **Frontend Design** (لو UI)
2. بعد الكتابة مباشرة: **Clean Code Guard** (كود) أو **Test Guard** (تستات)
3. قبل التسليم النهائي: **Web Design Guidelines** (لو UI) + **UX Writing** (لو فيه نص مستخدم)
4. عند طلب مراجعة بدل تنفيذ: **Code Review**

## 11. Environment & Secrets

- `.env` — للـsecrets الحقيقية فقط (OpenRouter API key، Gemini API key، Supabase keys) — **لا يترفع على GitHub** (في `.gitignore`)
- `docs/demo-accounts.md` — حسابات الـdemo الوهمية (إيميلات/باسوردز مش حقيقية) — ممكن تترفع عادي، مش secret

## 12. Progress Tracking

- كل أداة كود بتشتغل على المشروع (Cursor، Qoder، opencode، إلخ) لازم في **آخر** كل مهمة تكتب ملخص لما تم إنجازه في ملف `docs/PROGRESS.md`
- **أول مرة الملف مش موجود:** الأداة تنشئه هي نفسها جوه `docs/` بنفس الـformat تحت
- **الـformat:** entry جديد (مش استبدال القديم) لكل مهمة، بالترتيب الزمني:

```markdown
## [التاريخ] — [اسم المرحلة/المهمة]

**تم:**
- وصف مختصر لكل حاجة اتعملت

**ملفات اتعملت/اتعدلت:**
- path/to/file.py — وصف سطر واحد

**ملاحظات/قرارات اتاخدت أثناء التنفيذ:** (لو فيه)
- أي قرار مش موجود في الـspec الأصلي واضطرت الأداة تاخده

**الحالة:** ✅ تم / ⚠️ تم جزئياً (التفاصيل)
```

- الهدف: أي شات جديد (أو أي حد تاني) يقدر يفهم تاريخ التنفيذ كامل من غير ما يرجع لكل البرومتات القديمة