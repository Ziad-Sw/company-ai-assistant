"use client";

import { useTranslations } from "next-intl";

import { Dropdown } from "@/components/ui/Dropdown";

import type { ChatModel } from "../api/models";

type ModelDropdownProps = {
  models: ChatModel[] | null;
  loadFailed: boolean;
  selectedModel: string | null;
  onSelect: (modelId: string) => void;
};

/**
 * اختيار الموديل (PRD 10.4) — عرض بس، الحالة جاية من useModels.
 * فشل الجلب أو قائمة فاضية ليهم empty state واضح مش dropdown فاضي
 * (Design-System: Dropdown).
 */
export function ModelDropdown({ models, loadFailed, selectedModel, onSelect }: ModelDropdownProps) {
  const t = useTranslations("chat.model");

  if (loadFailed) {
    return (
      <p className="text-sm text-error" role="alert">
        {t("loadFailed")}
      </p>
    );
  }
  if (models !== null && models.length === 0) {
    return (
      <p className="text-sm text-warning" role="alert">
        {t("noneAvailable")}
      </p>
    );
  }
  if (models === null || selectedModel === null) {
    return (
      <p className="text-sm text-muted" aria-live="polite">
        {t("loadingModels")}
      </p>
    );
  }

  return (
    <Dropdown
      ariaLabel={t("label")}
      placeholder={t("placeholder")}
      emptyLabel={t("noneAvailable")}
      options={models.map((model) => ({
        value: model.id,
        label: model.name,
        description:
          model.context_length !== null
            ? t("contextLength", { count: model.context_length })
            : undefined,
      }))}
      value={selectedModel}
      onChange={onSelect}
    />
  );
}
