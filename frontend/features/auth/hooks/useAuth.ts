"use client";

import { useEffect } from "react";

import { useAuthStore } from "@/store/authStore";

import { fetchMe } from "../api/me";
import { supabase } from "../api/supabase";
import type { AuthSession } from "@/store/authStore";

function toSession(session: { user: { id: string }; access_token: string; expires_at?: number | null }): AuthSession {
  return {
    userId: session.user.id,
    accessToken: session.access_token,
    expiresAt: session.expires_at ?? 0,
  };
}

/**
 * بيقرا الجلسة الحالية وبيركب onAuthStateChange مرة واحدة على مستوى الـapp
 * (بيُستدعى من layout الـ[locale]). كل تغيير في الجلسة بيتزامن مع الـstore:
 * دخول/تجديد صامت → setSession، خروج/فشل refresh → clear.
 *
 * أول ما الجلسة تثبت بنجيب GET /me مرة واحدة ونتخزن role/full_name للعرض
 * (الـbackend هو مصدر الحقيقة الوحيد للتفويض — هنا للواجهة بس).
 */
export function useAuthSync(): void {
  useEffect(() => {
    let profileFetch: Promise<void> | null = null;

    const syncProfile = (userId: string) => {
      if (profileFetch) return;
      profileFetch = fetchMe()
        .then((me) => {
          if (me.user_id !== userId) return;
          useAuthStore.getState().setProfile({ role: me.role, fullName: me.full_name });
        })
        .catch(() => {
          // فشل الـ/me مش بيقفل الجلسة — الـ401 هيتكشف من أول نداء فعلي،
          // والـapi client بيرد للمستخدم لصفحة الدخول في الحالتين.
          profileFetch = null;
        });
    };

    const { data } = supabase.auth.onAuthStateChange((_event, authSession) => {
      const store = useAuthStore.getState();
      if (authSession) {
        store.setSession(toSession(authSession));
        syncProfile(authSession.user.id);
      } else {
        profileFetch = null;
        store.clear();
      }
    });

    return () => data.subscription.unsubscribe();
  }, []);
}
