-- Migration 002 — RLS policies (الطبقة الثانية للحماية — Tech-Stack.md قسم 3 و6)
-- نفّذه مرة واحدة: Supabase Dashboard → SQL Editor → New query → الصق → Run
-- (آمن لو اتنفّذ تاني: كل الـstatements idempotent — drop if exists / or replace / enable متكرر).
--
-- القرار المعتمد: الـRLS دي **طبقة ثانوية** للحماية فقط — للوصول المباشر/المستقبلي
-- بـanon-key clients. الـbackend نفسه بيتصل بـPostgres بيوزر `postgres` (مالك
-- الجداول) فيتخطى الـRLS، والحماية الفعلية لكل /chat و/conversations هي
-- الفحص في كود التطبيق (app/auth/dependencies.py + فحص الصلاحية في الـagent).
--
-- ملاحظة مهمة: **بدون** `force row level security` — عشان المالك (postgres) يفضل
-- بيتخطى الـRLS وإلا الـbackend كله يتعطل.

-- ─── 1) دالة مساعدة: دور المستخدم الحالي من profiles ─────────────────────────
-- SECURITY DEFINER عشان البوليسي فيها تقرا من profiles من غير recursion
-- (بوليسي على profiles بتشاور على profiles نفسها بتعمل infinite recursion).
create or replace function public.get_my_role() returns text
language sql
stable
security definer
set search_path = ''
as $$
  select role from public.profiles where id = auth.uid()
$$;

revoke execute on function public.get_my_role() from public, anon;
grant execute on function public.get_my_role() to authenticated;

-- ─── 2) تفعيل الـRLS على كل الجداول ──────────────────────────────────────────
alter table public.profiles      enable row level security;
alter table public.documents     enable row level security;
alter table public.chunks        enable row level security;
alter table public.conversations enable row level security;
alter table public.messages      enable row level security;
alter table public.eval_runs     enable row level security;
-- audit_logs بيتفعّل في الـdo block تحت (الجدول بيتبني في Phase 3).

-- ─── 3) profiles: قراية صفّك بس + الـadmin يقرا الكل؛ INSERT/UPDATE للـadmin بس ──
drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own on public.profiles
  for select to authenticated
  using (id = auth.uid());

drop policy if exists profiles_select_all_admin on public.profiles;
create policy profiles_select_all_admin on public.profiles
  for select to authenticated
  using (public.get_my_role() = 'admin');

drop policy if exists profiles_insert_admin on public.profiles;
create policy profiles_insert_admin on public.profiles
  for insert to authenticated
  with check (public.get_my_role() = 'admin');

drop policy if exists profiles_update_admin on public.profiles;
create policy profiles_update_admin on public.profiles
  for update to authenticated
  using (public.get_my_role() = 'admin')
  with check (public.get_my_role() = 'admin');

-- ─── 4) documents: قراية حسب مصفوفة الـroles (PRD قسم 3)؛ الكتابة للـadmin بس ───
drop policy if exists documents_select_by_role on public.documents;
create policy documents_select_by_role on public.documents
  for select to authenticated
  using (
    public.get_my_role() = 'admin'
    or (
      public.get_my_role() = 'sales'
      and status = 'active'
      and category in ('property_listings', 'payment_policies', 'company_info_support')
    )
    or (
      public.get_my_role() = 'hr'
      and status = 'active'
      and category = 'company_info_support'
    )
  );

drop policy if exists documents_insert_admin on public.documents;
create policy documents_insert_admin on public.documents
  for insert to authenticated
  with check (public.get_my_role() = 'admin');

drop policy if exists documents_update_admin on public.documents;
create policy documents_update_admin on public.documents
  for update to authenticated
  using (public.get_my_role() = 'admin')
  with check (public.get_my_role() = 'admin');

-- ─── 5) chunks: القراية بس لو الـdocument الأب عدّى بوليسي القراية بتاعته ───────
-- الـsubquery هنا بيترشّح بـRLS الـdocuments نفسه، فالقاعدة الوحيدة المطلوبة هنا.
drop policy if exists chunks_select_via_document on public.chunks;
create policy chunks_select_via_document on public.chunks
  for select to authenticated
  using (exists (select 1 from public.documents d where d.id = document_id));

-- مفيش INSERT/UPDATE لأي دور authenticated — الكتابة service-only بس.

-- ─── 6) conversations: المالك بس (SELECT/UPDATE) + INSERT بـuser_id بتاعه ──────
drop policy if exists conversations_select_owner on public.conversations;
create policy conversations_select_owner on public.conversations
  for select to authenticated
  using (user_id = auth.uid());

drop policy if exists conversations_update_owner on public.conversations;
create policy conversations_update_owner on public.conversations
  for update to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists conversations_insert_owner on public.conversations;
create policy conversations_insert_owner on public.conversations
  for insert to authenticated
  with check (user_id = auth.uid());

-- ─── 7) messages: القراية بس لرسايل محادثة المالك؛ الكتابة service-only بس ─────
drop policy if exists messages_select_via_conversation on public.messages;
create policy messages_select_via_conversation on public.messages
  for select to authenticated
  using (exists (
    select 1 from public.conversations c
    where c.id = conversation_id and c.user_id = auth.uid()
  ));

-- ─── 8) eval_runs: قراية للـadmin بس؛ الكتابة service-only بس ──────────────────
drop policy if exists eval_runs_select_admin on public.eval_runs;
create policy eval_runs_select_admin on public.eval_runs
  for select to authenticated
  using (public.get_my_role() = 'admin');

-- ─── 9) audit_logs: نفس القاعدة — بس الجدول بيتعمل في Phase 3 (إدارة المستندات) ─
-- لسه مش موجود في الـschema الحالي (schema.sql مالوش audit_logs) — do block
-- عشان المايجريشن ده يتنفّذ كامل من غير فشل على الجدول الغايب.
do $$
begin
  if to_regclass('public.audit_logs') is not null then
    alter table public.audit_logs enable row level security;
    execute 'drop policy if exists audit_logs_select_admin on public.audit_logs';
    execute 'create policy audit_logs_select_admin on public.audit_logs
               for select to authenticated
               using (public.get_my_role() = ''admin'')';
  end if;
end $$;
