-- Company AI Assistant — Database Schema
-- نفّذ الملف ده في Supabase: Dashboard → SQL Editor → New query → الصق المحتوى → Run

-- 1) تفعيل الـextension بتاع pgvector (لازم أول حاجة)
create extension if not exists vector;

-- 2) جدول profiles — الأدوار (Sales / HR / Admin)
-- ملحوظة: Supabase Auth بيعمل جدول auth.users تلقائياً، إحنا بس بنضيف جدول profiles
-- مرتبط بيه عشان نخزّن الـrole وبيانات إضافية
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  role text not null check (role in ('sales', 'hr', 'admin')),
  created_at timestamptz not null default now()
);

-- 3) جدول documents — كل مستند مرفوع (بما فيه نسخه المختلفة)
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  doc_id text not null,              -- هوية منطقية مشتركة بين نسخ المستند الواحد
  title text not null,
  category text not null check (category in ('property_listings', 'payment_policies', 'company_info_support')),
  version text not null,
  language text not null default 'mixed',
  source_path text,                  -- مسار الملف الأصلي (للمرجعية)
  status text not null default 'active' check (status in ('active', 'inactive')),
  uploaded_by uuid references public.profiles(id),
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_documents_category on public.documents(category);
create index if not exists idx_documents_doc_id on public.documents(doc_id);

-- 4) جدول chunks — القطع النصية + الـvectors
-- الأبعاد 768 مطابقة لإعداد output_dimensionality في embeddings.py
create table if not exists public.chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  content text not null,
  embedding vector(768) not null,
  metadata jsonb not null default '{}'::jsonb,  -- {category, section (h2/h3), chunk_index}
  created_at timestamptz not null default now()
);

create index if not exists idx_chunks_document_id on public.chunks(document_id);

-- index للبحث بالتشابه (HNSW — أسرع وأحدث من IVFFlat لمعظم الحالات)
create index if not exists idx_chunks_embedding_hnsw
  on public.chunks using hnsw (embedding vector_cosine_ops);

-- 5) جدول conversations — تاريخ المحادثات
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text,
  created_at timestamptz not null default now()
);

-- 6) جدول messages — رسائل كل محادثة
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  sources jsonb not null default '[]'::jsonb,  -- مصادر رد الـassistant (migrations/001)
  created_at timestamptz not null default now()
);

create index if not exists idx_messages_conversation_id on public.messages(conversation_id);

-- 7) جدول eval_runs — نتائج RAGAS (هيُستخدم في Phase 4)
create table if not exists public.eval_runs (
  id uuid primary key default gen_random_uuid(),
  golden_question text not null,
  expected_source text,
  actual_answer text,
  score jsonb,
  created_at timestamptz not null default now()
);

-- ملحوظة: Row Level Security (RLS) للصلاحيات حسب الدور هتتضاف في خطوة لاحقة
-- بعد ما نبني الـauth flow، مش جزء من الـschema الأساسي ده.
