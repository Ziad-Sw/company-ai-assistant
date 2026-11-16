"use client";

import { useTranslations } from "next-intl";

import { supabase } from "@/features/auth/api/supabase";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/Button";

/**
 * Placeholder بسيط لصفحة /chat — إثبات إن مسار الدخول كامل شغال
 * (login → guard → /me → عرض الاسم والدور). واجهة الشات الفعلية في Phase لاحقة.
 */
export function ChatPlaceholder() {
  const t = useTranslations("chat");
  const fullName = useAuthStore((state) => state.profile?.fullName ?? "");
  const role = useAuthStore((state) => state.profile?.role ?? "");

  function handleSignOut() {
    // onAuthStateChange هيمسح الـstore، والـRequireAuth بيرجّع المستخدم
    // لصفحة الدخول بنفسه — مفيش navigation يدوي هنا.
    void supabase.auth.signOut();
  }

  return (
    <main className="flex min-h-full flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-xl font-semibold text-foreground">{fullName}</h1>
      <p className="text-sm text-muted">{role}</p>
      <div className="flex max-w-md flex-col gap-2 rounded-[var(--radius-lg)] border border-border bg-surface p-6">
        <p className="text-base font-medium text-foreground">{t("placeholderTitle")}</p>
        <p className="text-sm text-muted">{t("placeholderBody")}</p>
      </div>
      <Button variant="secondary" onClick={handleSignOut}>
        {t("signOut")}
      </Button>
    </main>
  );
}
