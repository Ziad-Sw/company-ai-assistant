"use client";

import { useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { usePathname, useRouter } from "@/i18n/navigation";

/** اللغة التانية لكل لغة — التبديل دايماً بين الـاثنين المتاحين. */
const TARGET_LOCALE = { en: "ar", ar: "en" } as const;

type Locale = keyof typeof TARGET_LOCALE;

/**
 * اسم اللغة الهدف بلغتها هي — عود مشترَك في الـswitchers عشان المستخدم
 * يلاقي اللغة اللي هينتقل ليها بصياغتها الأصلية مهما كانت لغة الواجهة.
 */
const TARGET_LABEL: Record<Locale, string> = {
  ar: "العربية",
  en: "English",
};

/**
 * مبدّل اللغة (Tech-Stack قسم 9: components/shared) — بيبدّل بادئة الـlocale
 * في المسار الحالي بنفس الصفحة، بـreplace مش push عشان زرار الرجوع مايرجعش
 * لنفس الصفحة بلغة تانية. الـdir والخط بيتبدلوا تلقائي من layout الـ[locale].
 */
export function LanguageSwitcher({ className }: { className?: string }) {
  const t = useTranslations("common");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  const target = TARGET_LOCALE[locale as Locale];
  if (!target) return null;

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => router.replace(pathname, { locale: target })}
      aria-label={t("switchLanguage")}
      className={className}
    >
      <span translate="no">{TARGET_LABEL[target]}</span>
    </Button>
  );
}
