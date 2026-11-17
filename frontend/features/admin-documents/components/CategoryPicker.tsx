"use client";

import { useTranslations } from "next-intl";

import { Dropdown } from "@/components/ui/Dropdown";

import { DOCUMENT_CATEGORIES } from "../types";

type CategoryPickerProps = {
  value: string | null;
  onChange: (category: string | null) => void;
  disabled?: boolean;
  /** للفلتر عايزين اختيار "الكل"، للرفع لازم اختيار. */
  includeAll?: boolean;
  className?: string;
};

/**
 * CategoryPicker (Tech-Stack §9) — wrapper على ui/Dropdown بخيارات
 * الـcategories الثلاثة بأسمائها المعروضة. الـonChange بيرجّع null للـ"الكل".
 */
export function CategoryPicker({ value, onChange, disabled, includeAll = false, className }: CategoryPickerProps) {
  const t = useTranslations("adminDocuments.categories");

  const options = [
    ...(includeAll
      ? [{ value: "__all__", label: t("all") }]
      : []),
    ...DOCUMENT_CATEGORIES.map((category) => ({ value: category, label: t(category) })),
  ];

  return (
    <Dropdown
      className={className}
      options={options}
      value={value ?? (includeAll ? "__all__" : null)}
      onChange={(selected) => onChange(selected === "__all__" ? null : selected)}
      placeholder={t("pickCategory")}
      emptyLabel={t("pickCategory")}
      ariaLabel={t("ariaLabel")}
      disabled={disabled}
    />
  );
}
