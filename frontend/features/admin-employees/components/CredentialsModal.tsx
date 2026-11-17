"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

import type { EmployeeCredentials } from "../types";

/**
 * عرض الكريدنشيالز مرة واحدة (PRD 10.6): إيميل + باسورد مؤقت مع تنبيه صريح
 * إنهم مش هيتعرضوا تاني — بعد الإغلاق مفيش استرجاع (إعادة التعيين مرحلة لاحقة).
 * الزرار بيلغي نفسه لو الـclipboard مش متاح بدل ما يكدب «اتنسخ».
 */
export function CredentialsModal({
  credentials,
  onClose,
}: {
  credentials: EmployeeCredentials;
  onClose: () => void;
}) {
  const t = useTranslations("adminEmployees.credentialsModal");
  const [copiedField, setCopiedField] = useState<"email" | "password" | null>(null);

  async function copy(field: "email" | "password", value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedField(field);
    } catch {
      setCopiedField(null);
    }
  }

  return (
    <Modal open onClose={onClose} title={t("title")}>
      <div className="flex flex-col gap-4">
        <div
          role="alert"
          className="rounded-[var(--radius-md)] border border-warning bg-warning-subtle px-3 py-2 text-sm text-foreground"
        >
          {t("warning")}
        </div>

        <p className="text-sm text-muted">{t("body", { name: credentials.full_name })}</p>

        <div className="flex flex-col gap-2">
          <CredentialRow
            label={t("emailLabel")}
            value={credentials.email}
            copied={copiedField === "email"}
            copyLabel={t("copy")}
            copiedLabel={t("copied")}
            onCopy={() => void copy("email", credentials.email)}
          />
          <CredentialRow
            label={t("passwordLabel")}
            value={credentials.temp_password}
            copied={copiedField === "password"}
            copyLabel={t("copy")}
            copiedLabel={t("copied")}
            onCopy={() => void copy("password", credentials.temp_password)}
          />
        </div>

        <div className="flex justify-end">
          <Button onClick={onClose}>{t("done")}</Button>
        </div>
      </div>
    </Modal>
  );
}

function CredentialRow({
  label,
  value,
  copied,
  copyLabel,
  copiedLabel,
  onCopy,
}: {
  label: string;
  value: string;
  copied: boolean;
  copyLabel: string;
  copiedLabel: string;
  onCopy: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2">
      <div className="min-w-0">
        <p className="text-xs text-muted">{label}</p>
        <p dir="ltr" className="select-all truncate font-mono text-sm text-foreground">
          {value}
        </p>
      </div>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        className="shrink-0"
        onClick={onCopy}
      >
        {copied ? copiedLabel : copyLabel}
      </Button>
    </div>
  );
}
