"use client";

import { useTranslations } from "next-intl";

/**
 * رسالة رفض الصلاحية (Design-System: Permission Denied Message) — خلفية
 * error-subtle ونص error وأيقونة قفل، والنص بتاع الـbackend نفسه (بيسمّي
 * السبب) — الواجهة بتعرضه زي ما هو.
 */
export function PermissionDeniedMessage({ message }: { message: string }) {
  const t = useTranslations("chat.denied");
  return (
    <div
      role="alert"
      className="me-auto flex max-w-[85%] items-start gap-2 rounded-[var(--radius-md)] bg-error-subtle px-4 py-3"
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="mt-0.5 size-4 shrink-0 text-error"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 1 1 8 0v4" strokeLinecap="round" />
      </svg>
      <div>
        <p className="text-sm font-medium text-error">{t("title")}</p>
        <p className="mt-0.5 text-sm text-error">{message}</p>
      </div>
    </div>
  );
}
