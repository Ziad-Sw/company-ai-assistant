"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { PlusIcon } from "@/components/ui/icons";

import { AddEmployeeModal } from "./AddEmployeeModal";
import { CredentialsModal } from "./CredentialsModal";
import { EmployeeTable } from "./EmployeeTable";
import { useEmployees } from "../hooks/useEmployees";
import type { EmployeeCredentials } from "../types";

/**
 * شاشة إدارة الموظفين كاملة (PRD 10.6): قايمة الفريق + إضافة موظف
 * بكريدنشيالز مؤقتة بتتعرض مرة واحدة. الـtranslation namespace الوحيد:
 * adminEmployees.
 */
export function EmployeesScreen() {
  const t = useTranslations("adminEmployees");
  const controller = useEmployees();
  const [showAddModal, setShowAddModal] = useState(false);
  const [credentials, setCredentials] = useState<EmployeeCredentials | null>(null);

  return (
    <div className="mx-auto flex h-full w-full max-w-6xl flex-col gap-4 overflow-y-auto p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-foreground">{t("title")}</h1>
          <p className="text-sm text-muted">{t("subtitle")}</p>
        </div>
        <Button onClick={() => setShowAddModal(true)}>
          <PlusIcon />
          {t("addButton")}
        </Button>
      </div>

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
      ) : controller.employees.length === 0 && !controller.isLoading ? (
        <div className="flex flex-col items-center gap-2 rounded-[var(--radius-lg)] border border-border bg-surface px-6 py-12 text-center">
          <p className="text-sm font-medium text-foreground">{t("empty")}</p>
          <p className="text-sm text-muted">{t("emptyHint")}</p>
        </div>
      ) : controller.isLoading ? (
        <p className="text-sm text-muted">{t("loading")}</p>
      ) : (
        <EmployeeTable employees={controller.employees} />
      )}

      {showAddModal ? (
        <AddEmployeeModal
          onClose={() => setShowAddModal(false)}
          onSubmit={async (payload) => {
            const created = await controller.add(payload);
            setShowAddModal(false);
            setCredentials(created);
          }}
        />
      ) : null}

      {credentials ? (
        <CredentialsModal credentials={credentials} onClose={() => setCredentials(null)} />
      ) : null}
    </div>
  );
}
