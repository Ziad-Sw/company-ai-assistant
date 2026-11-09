-- Migration 001 — مصادر رد الـassistant في جدول messages
-- نفّذه مرة واحدة في Supabase: Dashboard → SQL Editor → New query → الصق → Run
-- (آمن لو اتنفّذ تاني: if not exists). schema.sql اتحدّث بنفس العمود للإعدادات الجديدة.
--
-- الـformat: [{chunk_id, doc_id, doc_title, version, section, similarity_score}, ...]
-- رسايل الـuser بتتخزن بـ'[]'.
alter table public.messages
  add column if not exists sources jsonb not null default '[]'::jsonb;
