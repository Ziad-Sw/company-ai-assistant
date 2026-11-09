# Progress Log — Company AI Assistant

> سجل زمني لكل مهمة اتنفذت على المشروع (حسب `Tech-Stack.md` قسم 12). كل مهمة جديدة = entry جديد تحت، من غير ما نمسح القديم.

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
