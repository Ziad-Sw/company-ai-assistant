"use client";

import { useCallback, useLayoutEffect, useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { MoonIcon, SunIcon } from "@/components/ui/icons";

/** مفتاح التخزين — لازم يفضل مطابق للسكريبت الـinline في layout الـ[locale]. */
const THEME_KEY = "theme";

/**
 * نفس ترتيب الأولوية بتاع السكريبت الـinline (Design-System §5):
 * القيمة المخزنة أولاً، وإلا تفضيل النظام.
 */
function resolveStoredTheme(): boolean {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "dark") return true;
    if (stored === "light") return false;
  } catch {
    // localStorage مش متاح — نرجع لتفضيل النظام تحت.
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** الـstore الخارجي = كلاس .dark على الـhtml — بتتغير من السكريبت/التوغل/السكريبتات التانية. */
function subscribeToThemeClass(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
  return () => observer.disconnect();
}

function isDarkSnapshot(): boolean {
  return document.documentElement.classList.contains("dark");
}

/**
 * مبدّل الوضع الداكن (Tech-Stack قسم 9: components/shared) — بيبدّل كلاس
 * .dark على الـhtml ويحفظ الاختيار في localStorage. الكلاس نفسه بيحطه
 * السكريبت الـinline قبل أول paint، والمكوّن ده بيقرايه ويعدّله — الـstate
 * بيتزامن مع الـDOM عبر useSyncExternalStore فمفيش نسخة تانية منه.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const t = useTranslations("common");
  const isDark = useSyncExternalStore(
    subscribeToThemeClass,
    isDarkSnapshot,
    /** الـSSR دايماً light — السكريبت الـinline هو اللي بيصحّح قبل أول paint. */
    () => false
  );

  // إعادة تطبيق الوحدة المحفوظة — بيلتقط remount بتاع Strict Mode في الـdev
  // (اللي بيمسح الكلاس اللي حطه السكريبت). no-op في الإنتاج.
  useLayoutEffect(() => {
    document.documentElement.classList.toggle("dark", resolveStoredTheme());
  }, []);

  const toggleTheme = useCallback(() => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem(THEME_KEY, next ? "dark" : "light");
    } catch {
      // التبديل شغال — الحفظ best-effort بس (وضع خاص/تخزين محدود).
    }
  }, []);

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={toggleTheme}
      aria-label={t("toggleTheme")}
      aria-pressed={isDark}
      className={className}
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </Button>
  );
}
