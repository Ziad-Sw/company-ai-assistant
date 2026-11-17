-- Migration 003 — Phase 3: audit_logs + حالات المعالجة + الـStorage bucket
-- نفّذه مرة واحدة: Supabase Dashboard → SQL Editor → New query → الصق → Run
-- (آمن لو اتنفّذ تاني: كل الـstatements idempotent — if not exists / drop if exists / on conflict).
--
-- محتواه:
--   1) جدول audit_logs (Tech-Stack.md قسم 3) — مين عمل إيه وإمتى. الـtarget_id
--      **من غير foreign key** عمداً: سجل الحذف لازم يفضل موجود بعد ما صف
--      المستند يتمسح (PRD 10.5-د: الـaudit trail متاح حتى بعد الحذف).
--   2) توسيع حالات documents (PRD 10.5): processing/failed للرفع وإعادة
--      المعالجة — مش بس active/inactive.
--   3) Storage bucket خاص باسم documents (خاص، مش public) — ملفات الرفع
--      بتاعة الـPhase 3. الـbackend بيكتب ويقرا منه بـservice_role،
--      والـfrontend عمره ما بيوصله مباشرة، فمفيش storage policies مطلوبة.
--   4) RLS: audit_logs (قراية admin بس — نفس محتوى الـdo block في 002،
--      مع تفعيل الجدول دلوقتي إنه موجود) + documents delete للـadmin
--      (الحذف النهائي بقى operation رسمية في الـPhase ده).

-- ─── 1) audit_logs ────────────────────────────────────────────────────────────
create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references public.profiles(id),
  action text not null check (action in (
    'upload', 'edit', 'replace', 'deactivate', 'activate',
    'delete', 'reprocess', 'add_employee'
  )),
  target_type text not null check (target_type in ('document', 'employee')),
  target_id uuid not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_audit_logs_target
  on public.audit_logs(target_type, target_id);
create index if not exists idx_audit_logs_created_at
  on public.audit_logs(created_at desc);

-- ─── 2) حالات documents: processing/failed للمعالجة اللحظية (PRD 10.5-ب) ──────
-- الـconstraint الافتراضي من schema.sql اسمه documents_status_check (اسم Postgres
-- التلقائي: <table>_<column>_check). بنشيله ونحط الـموسّع بنفس الاسم.
alter table public.documents drop constraint if exists documents_status_check;
alter table public.documents add constraint documents_status_check
  check (status in ('active', 'inactive', 'processing', 'failed'));

-- ─── 3) Storage bucket لملفات الرفع ──────────────────────────────────────────
insert into storage.buckets (id, name, public, file_size_limit)
values ('documents', 'documents', false, 20971520)  -- 20 MB
on conflict (id) do nothing;

-- ─── 4) RLS ──────────────────────────────────────────────────────────────────
alter table public.audit_logs enable row level security;

drop policy if exists audit_logs_select_admin on public.audit_logs;
create policy audit_logs_select_admin on public.audit_logs
  for select to authenticated
  using (public.get_my_role() = 'admin');

-- الحذف النهائي للمستندات بقى عملية رسمية (PRD 10.5-ج) — بوليسي الحذف كانت
-- ناقصة في 002 لأن الحذف كان برا نطاق المرحلة ساعتها.
drop policy if exists documents_delete_admin on public.documents;
create policy documents_delete_admin on public.documents
  for delete to authenticated
  using (public.get_my_role() = 'admin');
