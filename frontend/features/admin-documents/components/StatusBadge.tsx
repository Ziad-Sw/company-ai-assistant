"use client";

import { useTranslations } from "next-intl";
import type { DocumentStatus } from "../types";

/**
 * بادج حالة المستند (PRD 10.5-أ) — توكنز الـDesign-System:
 * active=success، failed=error، processing=primary (مع spinner)، inactive=محايد.
 */
const STATUS_CLASSES: Record<DocumentStatus, string> = {
  active: "bg-success-subtle text-success",
  failed: "bg-error-subtle text-error",
  processing: "bg-primary-subtle text-primary",
  inactive: "bg-input text-muted border border-border",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const t = useTranslations("adminDocuments.status");
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-[var(--radius-full)] px-2.5 py-0.5 text-xs font-medium ${STATUS_CLASSES[status]}`}
    >
      {status === "processing" ? (
        <span
          aria-hidden="true"
          className="size-3 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      ) : null}
      {t(status)}
      {status === "processing" ? <span className="sr-only">(…)</span> : null}
    </span>
  );
}
