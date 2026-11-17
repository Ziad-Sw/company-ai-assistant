"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useLocale } from "next-intl";

import { supabase } from "@/features/auth/api/supabase";

/**
 * الـroot بتاع الـlocale (زي /en و/ar) مفيهوش صفحة — بنوجّه المستخدم حسب
 * الجلسة: مسجّل دخول → /{locale}/chat على طول، مش مسجّل → /{locale}/login.
 * الجلسة بتتخزن client-side (Supabase localStorage) فالقرار لازم يكون هنا.
 * لو الجلسة كانت قديمة، الـguard في /(chat) هو اللي هيردّه للـlogin.
 */
export default function LocaleRootPage() {
  const router = useRouter();
  const locale = useLocale();

  useEffect(() => {
    let cancelled = false;
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      router.replace(data.session ? `/${locale}/chat` : `/${locale}/login`);
    });
    return () => {
      cancelled = true;
    };
  }, [locale, router]);

  return null;
}
