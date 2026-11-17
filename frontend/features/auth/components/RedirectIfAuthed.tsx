"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useLocale } from "next-intl";

import { supabase } from "../api/supabase";

/**
 * بيتركب جوه صفحة الـlogin: لو فيه جلسة قائمة أصلاً بننقل المستخدم
 * للـchat مباشرة بدل ما يسجّل دخول تاني (زي أغلب التطبيقات).
 */
export function RedirectIfAuthed() {
  const router = useRouter();
  const locale = useLocale();

  useEffect(() => {
    let cancelled = false;
    supabase.auth.getSession().then(({ data }) => {
      if (!cancelled && data.session) {
        router.replace(`/${locale}/chat`);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [locale, router]);

  return null;
}
