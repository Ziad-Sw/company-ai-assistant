/** cn() helper — Tech-Stack.md قسم 9 (lib/utils.ts). */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * تنسيق التاريخ والوقت بلغة الواجهة الحالية — لعرض عمود "آخر تحديث"
 * وسجل الـaudit. الـclient-side بس (الصفحات الإدارية بتنده بعد الـmount).
 */
export function formatDateTime(isoString: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-EG" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoString));
}
