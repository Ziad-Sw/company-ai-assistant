"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useLocale } from "next-intl";

import { useAuthStore } from "@/store/authStore";

/**
 * الـroute guard: بيرندر المحتوى بس لو فيه جلسة، وغير كده بيرجّع المستخدم
 * لصفحة الدخول. حماية عرض بس (ومنع وميض المحتوى) — الحماية الفعلية على
 * الـbackend: أي نداء بدون JWT بيرجع 401 والـapi client بيرجّع للدخول برضه.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const locale = useLocale();
  const session = useAuthStore((state) => state.session);

  useEffect(() => {
    if (!session) {
      router.replace(`/${locale}/login`);
    }
  }, [session, locale, router]);

  if (!session) {
    return null;
  }
  return <>{children}</>;
}

/**
 * نفس الـguard + بوابة الـadmin للعرض (مفيدة لـ/(admin)/* لما صفحات Phase 3
 * تتبني). الـrole هنا من GET /me على السيرفر — والـendpoints الإدارية على
 * الـbackend عليها require_admin هو القرار النهائي.
 */
export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const locale = useLocale();
  const session = useAuthStore((state) => state.session);
  const role = useAuthStore((state) => state.profile?.role ?? null);

  useEffect(() => {
    if (!session) {
      router.replace(`/${locale}/login`);
    }
  }, [session, locale, router]);

  useEffect(() => {
    if (session && role !== null && role !== "admin") {
      router.replace(`/${locale}/chat`);
    }
  }, [session, role, locale, router]);

  if (!session || role !== "admin") {
    return null;
  }
  return <>{children}</>;
}
