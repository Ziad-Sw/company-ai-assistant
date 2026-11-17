"use client";

import { useLocale, useTranslations } from "next-intl";

import {
  ClockIcon,
  ListIcon,
  PencilIcon,
  RefreshIcon,
  TrashIcon,
  UploadIcon,
} from "@/components/ui/icons";
import { formatDateTime } from "@/lib/utils";

import { StatusBadge } from "./StatusBadge";
import type { DocumentsController } from "../hooks/useDocuments";
import type { DocumentSummary } from "../types";

type DocumentTableProps = {
  controller: DocumentsController;
  onEdit: (document: DocumentSummary) => void;
  onReplace: (document: DocumentSummary) => void;
  onVersions: (document: DocumentSummary) => void;
  onAudit: (document: DocumentSummary) => void;
  onDelete: (document: DocumentSummary) => void;
};

/**
 * جدول المستندات (PRD 10.5-أ) — عمود أكشنز بأيقونات sm مع aria-labels
 * (بديل قايمة منسدلة عشان الـDropdown المشترك قايمة اختيار مش menu
 * أوامر). صف processing بيتعطل كل الأكشنز غير القراية (409 من الـbackend
 * برضه — حماية مزدوجة). المساحة الضيقة بتعمل scroll أفقي.
 */
export function DocumentTable({
  controller,
  onEdit,
  onReplace,
  onVersions,
  onAudit,
  onDelete,
}: DocumentTableProps) {
  const t = useTranslations("adminDocuments");
  const locale = useLocale();
  const { documents, busyDocumentId, reprocess, patch } = controller;

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-border bg-surface">
      <table className="w-full min-w-[860px] text-start text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-muted">
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.document")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.category")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.version")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.status")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.uploadedBy")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.updatedAt")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.actions")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {documents.map((document) => {
            const isBusy = busyDocumentId === document.id;
            const isLocked = document.status === "processing" || isBusy;
            return (
              <tr key={document.id} className="text-foreground">
                <td className="max-w-[240px] px-4 py-3">
                  <p className="truncate font-medium">{document.title}</p>
                  <p className="truncate text-xs text-muted">{document.doc_id}</p>
                </td>
                <td className="px-4 py-3">{t(`categories.${document.category}`)}</td>
                <td className="px-4 py-3 tabular-nums">{document.version}</td>
                <td className="px-4 py-3"><StatusBadge status={document.status} /></td>
                <td className="px-4 py-3">{document.uploaded_by_name ?? "—"}</td>
                <td className="px-4 py-3 text-xs text-muted">
                  {formatDateTime(document.updated_at, locale)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <RowAction
                      label={t("actions.editCategory")}
                      disabled={isLocked}
                      onClick={() => onEdit(document)}
                    >
                      <PencilIcon />
                    </RowAction>
                    <RowAction
                      label={t("actions.replace")}
                      disabled={isLocked}
                      onClick={() => onReplace(document)}
                    >
                      <UploadIcon />
                    </RowAction>
                    <RowAction
                      label={t("actions.reprocess")}
                      disabled={isLocked}
                      onClick={() => reprocess(document.id)}
                    >
                      <RefreshIcon />
                    </RowAction>
                    <RowAction
                      label={t("actions.versions")}
                      onClick={() => onVersions(document)}
                    >
                      <ClockIcon />
                    </RowAction>
                    <RowAction label={t("actions.audit")} onClick={() => onAudit(document)}>
                      <ListIcon />
                    </RowAction>
                    {document.status === "active" || document.status === "inactive" ? (
                      <RowAction
                        label={document.status === "active" ? t("actions.deactivate") : t("actions.activate")}
                        disabled={isLocked}
                        onClick={() =>
                          patch(document.id, {
                            status: document.status === "active" ? "inactive" : "active",
                          })
                        }
                      >
                        <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2">
                          {document.status === "active" ? (
                            <path d="M10 5H7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3m7-9 3 3-3 3m-8-3h11" strokeLinecap="round" strokeLinejoin="round" />
                          ) : (
                            <path d="M14 5h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-3M4 12h11m3-3-3 3 3 3" strokeLinecap="round" strokeLinejoin="round" />
                          )}
                        </svg>
                      </RowAction>
                    ) : null}
                    <RowAction
                      label={t("actions.delete")}
                      danger
                      disabled={isLocked}
                      onClick={() => onDelete(document)}
                    >
                      <TrashIcon />
                    </RowAction>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RowAction({
  label,
  disabled = false,
  danger = false,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  danger?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={`flex size-8 items-center justify-center rounded-[var(--radius-sm)] text-muted
        hover:bg-primary-subtle hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-0
        focus-visible:outline-primary/30 disabled:pointer-events-none disabled:opacity-40
        ${danger ? "hover:bg-error-subtle hover:text-error" : ""}`}
    >
      {children}
    </button>
  );
}
