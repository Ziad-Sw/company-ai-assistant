"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { Modal } from "@/components/ui/Modal";
import { formatDateTime } from "@/lib/utils";

import { listDocumentVersions } from "../api/documents";
import type { DocumentSummary } from "../types";
import { StatusBadge } from "./StatusBadge";

type VersionHistoryModalProps = {
  document: DocumentSummary;
  onClose: () => void;
};

/**
 * VersionHistoryModal (PRD 10.5-ب) — كل نسخ نفس doc_id بحالاتها، الأحدث
 * أولاً. الجلب في effect بـpromise callback بس (مفيش setState متزامن)،
 * والبيانات بتجيب مرة واحدة عند التركيب (الـparent بيعمل render مشروط
 * فالحالة بتتصفّر تلقائياً مع كل فتح).
 */
export function VersionHistoryModal({ document, onClose }: VersionHistoryModalProps) {
  const t = useTranslations("adminDocuments.versions");
  const locale = useLocale();
  const [versions, setVersions] = useState<DocumentSummary[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listDocumentVersions(document.id)
      .then((rows) => {
        if (!cancelled) setVersions(rows);
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
      {versions === null && !loadFailed ? <p className="text-sm text-muted">{t("loading")}</p> : null}
      {loadFailed ? <p role="alert" className="text-sm text-error">{t("loadFailed")}</p> : null}
      {versions !== null ? (
        versions.length === 0 ? (
          <p className="text-sm text-muted">{t("empty")}</p>
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {versions.map((version) => (
              <li key={version.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">
                    {t("versionLabel", { version: version.version })}
                    {version.id === document.id ? (
                      <span className="ms-2 text-xs font-normal text-muted">{t("current")}</span>
                    ) : null}
                  </p>
                  <p className="truncate text-xs text-muted">
                    {version.uploaded_by_name ?? "—"} · {formatDateTime(version.created_at, locale)}
                  </p>
                </div>
                <StatusBadge status={version.status} />
              </li>
            ))}
          </ul>
        )
      ) : null}
    </Modal>
  );
}
