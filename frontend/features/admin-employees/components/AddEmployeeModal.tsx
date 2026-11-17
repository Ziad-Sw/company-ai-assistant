"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { Dropdown } from "@/components/ui/Dropdown";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";

import { EMAIL_LOCAL_PATTERN, EMPLOYEE_ROLES, type EmployeeRole } from "../types";

/**
 * مودال إضافة موظف (PRD 10.6): الاسم + الـrole + الـemail local-part.
 * الإيميل الكامل بيتكون من local@reelestate.demo (قرار 2026-11-17: مفيش
 * توليد تلقائي من الاسم — الأسامي العربية مش صالحة كإيميل). تحقق مبكر
 * بنفس pattern الـbackend عشان رسالة أسرع من الـ422.
 */
export function AddEmployeeModal({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (payload: { full_name: string; role: EmployeeRole; email_local: string }) => Promise<void>;
}) {
  const t = useTranslations("adminEmployees");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<EmployeeRole | null>(null);
  const [emailLocal, setEmailLocal] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const roleOptions = EMPLOYEE_ROLES.map((value) => ({
    value,
    label: t(`roles.${value}`),
    description: t(`roleDescriptions.${value}`),
  }));

  async function submit() {
    const trimmedName = fullName.trim();
    const trimmedLocal = emailLocal.trim();
    if (!trimmedName) {
      setValidationError(t("addModal.errorName"));
      return;
    }
    if (!role) {
      setValidationError(t("addModal.errorRole"));
      return;
    }
    if (!EMAIL_LOCAL_PATTERN.test(trimmedLocal)) {
      setValidationError(t("addModal.errorEmail"));
      return;
    }
    setValidationError(null);
    try {
      await onSubmit({ full_name: trimmedName, role, email_local: trimmedLocal });
    } catch {
      // خطأ الـbackend بيتعرض في الـbanner — المودال بيفضل مفتوح للتصحيح
    }
  }

  return (
    <Modal open onClose={onClose} title={t("addModal.title")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <div className="flex flex-col gap-1.5">
          <label htmlFor="employee-name" className="text-sm font-medium text-foreground">
            {t("addModal.nameLabel")}
          </label>
          <Input
            id="employee-name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            placeholder={t("addModal.namePlaceholder")}
            maxLength={120}
            autoFocus
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-foreground">{t("addModal.roleLabel")}</span>
          <Dropdown
            options={roleOptions}
            value={role}
            onChange={(value) => setRole(value as EmployeeRole)}
            placeholder={t("addModal.rolePlaceholder")}
            emptyLabel={t("addModal.rolePlaceholder")}
            ariaLabel={t("addModal.roleAriaLabel")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="employee-email" className="text-sm font-medium text-foreground">
            {t("addModal.emailLabel")}
          </label>
          <Input
            id="employee-email"
            type="text"
            dir="ltr"
            value={emailLocal}
            onChange={(event) => setEmailLocal(event.target.value.toLowerCase())}
            placeholder={t("addModal.emailPlaceholder")}
            maxLength={64}
            inputMode="text"
            autoCapitalize="none"
            autoComplete="off"
            spellCheck={false}
          />
          <p className="text-xs text-muted">{t("addModal.emailHint")}</p>
        </div>

        {validationError ? (
          <p role="alert" className="text-sm text-error">{validationError}</p>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>{t("addModal.cancel")}</Button>
          <Button type="submit">{t("addModal.submit")}</Button>
        </div>
      </form>
    </Modal>
  );
}
