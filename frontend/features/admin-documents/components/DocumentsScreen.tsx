"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlusIcon } from "@/components/ui/icons";

import { CategoryPicker } from "./CategoryPicker";
import { AuditLogPanel } from "./AuditLogPanel";
import { DocumentFilters } from "./DocumentFilters";
import { DocumentTable } from "./DocumentTable";
import { DocumentUploader, type UploaderState } from "./DocumentUploader";
import { VersionHistoryModal } from "./VersionHistoryModal";
import { useDocuments } from "../hooks/useDocuments";
import type { DocumentSummary } from "../types";

/**
 * شاشة إدارة المستندات كاملة (PRD 10.5): قايمة مع فلترة وبحث، رفع/استبدال
 * بـpolling لحالة المعالجة، تعديل category، تفعيل/تعطيل، حذف بتأكيد إلزامي،
 * سجل نسخ، وسجل audit. الـtranslation namespace الوحيد: adminDocuments.
 */
export function DocumentsScreen() {
  const t = useTranslations("adminDocuments");
  const controller = useDocuments();
  const [uploader, setUploader] = useState<UploaderState | null>(null);
  const [editing, setEditing] = useState<DocumentSummary | null>(null);
  const [editCategory, setEditCategory] = useState<string | null>(null);
  const [versionTarget, setVersionTarget] = useState<DocumentSummary | null>(null);
  const [auditTarget, setAuditTarget] = useState<DocumentSummary | null>(null);
  const [deleting, setDeleting] = useState<DocumentSummary | null>(null);

  const hasFilters = Boolean(controller.category || controller.searchInput);

  return (
    <div className="mx-auto flex h-full w-full max-w-6xl flex-col gap-4 overflow-y-auto p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-foreground">{t("title")}</h1>
          <p className="text-sm text-muted">{t("subtitle")}</p>
        </div>
        <Button onClick={() => setUploader({ mode: "upload" })}>
          <PlusIcon />
          {t("uploadButton")}
        </Button>
      </div>

      <DocumentFilters controller={controller} />

      {controller.actionError ? (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-error bg-error-subtle px-3 py-2 text-sm text-error"
        >
          <span className="min-w-0 break-words">{controller.actionError}</span>
          <button
            type="button"
            onClick={controller.clearActionError}
            aria-label={t("dismissError")}
            className="shrink-0 rounded-[var(--radius-sm)] px-2 py-1 hover:bg-error/10 focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-error/40"
          >
            {t("dismiss")}
          </button>
        </div>
      ) : null}

      {controller.loadFailed ? (
        <div className="flex flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-border bg-surface px-6 py-12 text-center">
          <p className="text-sm text-muted">{t("loadFailed")}</p>
          <Button variant="secondary" onClick={controller.reload}>{t("retry")}</Button>
        </div>
      ) : controller.documents.length === 0 && !controller.isLoading ? (
        <div className="flex flex-col items-center gap-2 rounded-[var(--radius-lg)] border border-border bg-surface px-6 py-12 text-center">
          <p className="text-sm font-medium text-foreground">
            {hasFilters ? t("emptyFiltered") : t("empty")}
          </p>
          <p className="text-sm text-muted">{t("emptyHint")}</p>
        </div>
      ) : controller.isLoading ? (
        <p className="text-sm text-muted">{t("loading")}</p>
      ) : (
        <DocumentTable
          controller={controller}
          onEdit={(document) => {
            setEditing(document);
            setEditCategory(document.category);
          }}
          onReplace={(document) =>
            setUploader({
              mode: "replace",
              documentId: document.id,
              documentTitle: document.title,
              documentVersion: document.version,
            })
          }
          onVersions={setVersionTarget}
          onAudit={setAuditTarget}
          onDelete={setDeleting}
        />
      )}

      {uploader ? (
        <DocumentUploader
          state={uploader}
          onClose={() => setUploader(null)}
          onSubmit={async (file, category) => {
            try {
              if (uploader.mode === "replace" && uploader.documentId) {
                await controller.replace(uploader.documentId, file);
              } else {
                await controller.upload(file, category);
              }
              setUploader(null);
            } catch {
              // الخطأ بيتصير جوه الـhook (actionError) — المودال بيفضل مفتوح للتصحيح
            }
          }}
        />
      ) : null}

      <Modal
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        title={t("editModal.title")}
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted">{t("editModal.hint", { title: editing?.title ?? "" })}</p>
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-foreground">{t("editModal.categoryLabel")}</span>
            <CategoryPicker value={editCategory} onChange={setEditCategory} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setEditing(null)}>{t("editModal.cancel")}</Button>
            <Button
              disabled={!editCategory || editCategory === editing?.category}
              onClick={() => {
                if (!editing || !editCategory) return;
                controller.patch(editing.id, { category: editCategory });
                setEditing(null);
              }}
            >
              {t("editModal.save")}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={Boolean(deleting)}
        onClose={() => setDeleting(null)}
        title={t("deleteModal.title")}
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-foreground">{t("deleteModal.body", { title: deleting?.title ?? "" })}</p>
          <p className="text-sm text-muted">{t("deleteModal.warning")}</p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeleting(null)}>{t("deleteModal.cancel")}</Button>
            <Button
              variant="danger"
              onClick={() => {
                if (!deleting) return;
                controller.remove(deleting.id);
                setDeleting(null);
              }}
            >
              {t("deleteModal.confirm")}
            </Button>
          </div>
        </div>
      </Modal>

      {versionTarget ? (
        <VersionHistoryModal document={versionTarget} onClose={() => setVersionTarget(null)} />
      ) : null}
      {auditTarget ? (
        <AuditLogPanel document={auditTarget} onClose={() => setAuditTarget(null)} />
      ) : null}
    </div>
  );
}
