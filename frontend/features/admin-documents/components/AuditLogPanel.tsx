"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { Modal } from "@/components/ui/Modal";
import { formatDateTime } from "@/lib/utils";

import { listDocumentAudit } from "../api/documents";
import type { AuditEntry, DocumentSummary } from "../types";

type AuditLogPanelProps = {
  document: DocumentSummary;
  onClose: () => void;
};

/**
 * AuditLogPanel (PRD 10.5-د) — سجل بسيط تحت المستند (مش صفحة منفصلة):
 * مين عمل العملية وإمتى. الجلب في effect بـpromise callback بس، والـparent
 * بيعمل render مشروط فالحالة بتتصفّر تلقائياً مع كل فتح. مستند متمسح لسه
 * سجله متاح من الـbackend (الـendpoint بيرجّع 200 لو فيه سجل).
 */
export function AuditLogPanel({ document, onClose }: AuditLogPanelProps) {
  const t = useTranslations("adminDocuments.audit");
  const locale = useLocale();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listDocumentAudit(document.id)
      .then((rows) => {
        if (!cancelled) setEntries(rows);
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [document]);

  return (
    <Modal open onClose={onClose} title={t("title")} wide>
      {entries === null && !loadFailed ? <p className="text-sm text-muted">{t("loading")}</p> : null}
      {loadFailed ? <p role="alert" className="text-sm text-error">{t("loadFailed")}</p> : null}
      {entries !== null ? (
        entries.length === 0 ? (
          <p className="text-sm text-muted">{t("empty")}</p>
        ) : (
          <ol className="flex flex-col divide-y divide-border">
            {entries.map((entry) => (
              <li key={entry.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">
                    {t(`actions.${entry.action}`)}
                  </p>
                  <p className="truncate text-xs text-muted">{entry.actor_name ?? "—"}</p>
                </div>
                <time dateTime={entry.created_at} className="text-xs text-muted">
                  {formatDateTime(entry.created_at, locale)}
                </time>
              </li>
            ))}
          </ol>
        )
      ) : null}
    </Modal>
  );
}
